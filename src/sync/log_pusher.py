"""
Push structured error reports to the GitHub repo for automated triage.

Flow:
  1. Unhandled exception or critical error occurs
  2. This module serializes a sanitized error report (no images, no secrets)
  3. Commits it to error_reports/ in the repo
  4. Pushes to a dedicated branch
  5. GitHub Actions workflow detects the new file and triggers a coding agent
"""

import json
import time
import traceback
import subprocess
import platform
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorLogPusher:
    def __init__(
        self,
        repo_dir: str = "/opt/fishfluencer",
        error_dir: str = "error_reports",
        remote_branch_prefix: str = "error-report",
    ):
        self.repo_dir = Path(repo_dir)
        self.error_dir = self.repo_dir / error_dir
        self.error_dir.mkdir(parents=True, exist_ok=True)
        self.branch_prefix = remote_branch_prefix

    def report_error(
        self,
        exception: Exception,
        context: Optional[dict] = None,
    ) -> Optional[str]:
        """Create and push a structured error report."""
        timestamp = int(time.time())
        report_id = f"err_{timestamp}"
        branch_name = f"{self.branch_prefix}/{report_id}"

        report = {
            "report_id": report_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                ),
            },
            "system": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            },
            "context": self._sanitize_context(context or {}),
            "suggested_files": self._guess_relevant_files(exception),
        }

        report_path = self.error_dir / f"{report_id}.json"
        report_path.write_text(json.dumps(report, indent=2))

        try:
            self._git("checkout", "-b", branch_name)
            self._git("add", str(report_path.relative_to(self.repo_dir)))
            self._git(
                "commit",
                "-m",
                f"error-report: {type(exception).__name__} in "
                f"{self._extract_module(exception)}",
            )
            self._git("push", "origin", branch_name)
            logger.info("Error report pushed: %s", branch_name)

            self._git("checkout", "main")
            return branch_name

        except subprocess.CalledProcessError as e:
            logger.error("Failed to push error report: %s", e)
            try:
                self._git("checkout", "main")
            except Exception:
                pass
            return None

    def _sanitize_context(self, context: dict) -> dict:
        """Strip any sensitive data (API keys, file paths to images, etc.)."""
        sanitized = {}
        sensitive_keys = {"api_key", "secret", "password", "token", "image", "frame"}
        for k, v in context.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 1000:
                sanitized[k] = v[:500] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized

    def _extract_module(self, exc: Exception) -> str:
        """Extract the module name from the traceback."""
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            return Path(tb[-1].filename).stem
        return "unknown"

    def _guess_relevant_files(self, exc: Exception) -> list:
        """List source files from the traceback for the coding agent."""
        tb = traceback.extract_tb(exc.__traceback__)
        files = []
        for frame in tb:
            rel = Path(frame.filename)
            if "fishfluencer" in str(rel) or "src/" in str(rel):
                files.append(str(rel))
        return list(set(files))

    def _git(self, *args: str) -> str:
        cmd = ["git", "-C", str(self.repo_dir)] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=True
        )
        return result.stdout
