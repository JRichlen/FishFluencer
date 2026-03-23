"""
OTA update system via GitHub repository sync.

How it works:
  1. A systemd timer fires every N minutes
  2. This agent does a `git pull` from the configured remote
  3. If files changed, it optionally restarts the main service
  4. No SSH, VPN, or port-forwarding required — outbound HTTPS only
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubSyncAgent:
    def __init__(
        self,
        repo_dir: str = "/opt/fishfluencer",
        branch: str = "main",
        service_name: str = "fishfluencer.service",
        post_update_script: Optional[str] = "scripts/install_deps.sh",
    ):
        self.repo_dir = Path(repo_dir)
        self.branch = branch
        self.service_name = service_name
        self.post_update_script = post_update_script

    def sync(self) -> dict:
        """Pull latest changes and restart service if needed."""
        result = {
            "action": "sync",
            "changed": False,
            "restarted": False,
            "error": None,
        }

        try:
            old_hash = self._get_head_hash()
            self._run_git("fetch", "origin", self.branch)
            self._run_git("pull", "origin", self.branch, "--ff-only")
            new_hash = self._get_head_hash()

            result["old_hash"] = old_hash[:8]
            result["new_hash"] = new_hash[:8]

            if old_hash != new_hash:
                result["changed"] = True
                logger.info("Updated: %s → %s", old_hash[:8], new_hash[:8])

                if self.post_update_script:
                    script = self.repo_dir / self.post_update_script
                    if script.exists():
                        logger.info("Running post-update: %s", script)
                        subprocess.run(
                            ["bash", str(script)],
                            cwd=str(self.repo_dir),
                            check=True,
                            timeout=120,
                        )

                subprocess.run(
                    ["sudo", "systemctl", "restart", self.service_name],
                    check=True,
                    timeout=30,
                )
                result["restarted"] = True
                logger.info("Service %s restarted.", self.service_name)
            else:
                logger.debug("Already up to date.")

        except subprocess.CalledProcessError as e:
            result["error"] = f"Command failed: {e.cmd} → {e.returncode}"
            logger.error(result["error"])
        except Exception as e:
            result["error"] = str(e)
            logger.error("Sync failed: %s", e)

        return result

    def _get_head_hash(self) -> str:
        return self._run_git("rev-parse", "HEAD").strip()

    def _run_git(self, *args: str) -> str:
        cmd = ["git", "-C", str(self.repo_dir)] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=True
        )
        return result.stdout
