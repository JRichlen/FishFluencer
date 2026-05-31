"""
Push structured error reports to the GitHub repo for automated triage.

Flow:
  1. Unhandled exception or critical error occurs.
  2. This module serializes a sanitized error report (no images, no
     secrets).
  3. Commits it to error_reports/ in the repo.
  4. Pushes to a dedicated branch.
  5. A GitHub Actions workflow detects the new file and triggers a
     coding agent.
  6. The agent analyzes the error and proposes a fix PR.
  7. A human reviews and merges.
"""

import json
import logging
import platform
import re
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Patterns that look like secrets. Each is replaced with [REDACTED].
# We err on the side of over-redaction — the auto-fix agent can still
# work from the redacted form, and the report gets pushed to a public
# branch.
_SECRET_PATTERNS = [
    # Anthropic / OpenAI / GitHub-style tokens
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    # Generic bearer tokens
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),
    # AWS keys
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # JWT-like
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    # `password=...` / `token=...` / `api_key=...` query/kwargs
    re.compile(r"(?i)(password|token|api_key|secret)\s*[=:]\s*['\"]?[^\s'\"]+"),
    # Absolute user paths
    re.compile(r"/home/[^/\s]+"),
    re.compile(r"/Users/[^/\s]+"),
]


def _redact(s: str) -> str:
    for pat in _SECRET_PATTERNS:
        s = pat.sub("[REDACTED]", s)
    return s

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
        timestamp = int(time.time())
        report_id = f"err_{timestamp}"
        branch_name = f"{self.branch_prefix}/{report_id}"

        report = {
            "report_id": report_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": {
                "type": type(exception).__name__,
                "message": _redact(str(exception)),
                "traceback": [
                    _redact(line)
                    for line in traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                ],
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
                "commit", "-m",
                f"error-report: {type(exception).__name__} in "
                f"{self._extract_module(exception)}"
            )
            self._git("push", "origin", branch_name)
            logger.info("Error report pushed: %s", branch_name)

            # Best-effort return to main; ignore failures.
            try:
                self._git("checkout", "main")
            except Exception:
                pass
            return branch_name

        except subprocess.CalledProcessError as e:
            logger.error("Failed to push error report: %s", e)
            try:
                self._git("checkout", "main")
            except Exception:
                pass
            return None

    def _sanitize_context(self, context: dict) -> dict:
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
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            return Path(tb[-1].filename).stem
        return "unknown"

    def _guess_relevant_files(self, exc: Exception) -> List[str]:
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
