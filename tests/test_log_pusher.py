"""Tests for src/sync/log_pusher.py"""

import json
import subprocess
from unittest.mock import MagicMock, patch

from sync.log_pusher import ErrorLogPusher


class TestErrorLogPusher:
    def test_init(self, tmp_path):
        pusher = ErrorLogPusher(
            repo_dir=str(tmp_path),
            error_dir="errors",
        )
        assert (tmp_path / "errors").exists()
        assert pusher.branch_prefix == "error-report"

    def test_sanitize_context_redacts_sensitive(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        ctx = {
            "api_key": "sk-secret-123",
            "password": "hunter2",
            "phase": "testing",
            "token_value": "tok-abc",
        }
        sanitized = pusher._sanitize_context(ctx)
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["token_value"] == "[REDACTED]"
        assert sanitized["phase"] == "testing"

    def test_sanitize_context_truncates_long_values(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        ctx = {"data": "x" * 2000}
        sanitized = pusher._sanitize_context(ctx)
        assert sanitized["data"].endswith("...[truncated]")
        assert len(sanitized["data"]) < 2000

    def test_sanitize_context_empty(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        assert pusher._sanitize_context({}) == {}

    def test_extract_module(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        try:
            raise ValueError("test error")
        except ValueError as e:
            module = pusher._extract_module(e)
            assert module == "test_log_pusher"

    def test_extract_module_no_traceback(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        exc = ValueError("no tb")
        exc.__traceback__ = None
        assert pusher._extract_module(exc) == "unknown"

    def test_guess_relevant_files(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        try:
            raise ValueError("test")
        except ValueError as e:
            files = pusher._guess_relevant_files(e)
            # The test file itself may or may not match the fishfluencer/src filter
            assert isinstance(files, list)

    def test_guess_relevant_files_with_matching_path(self, tmp_path):
        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        ValueError("test")
        # Create a fake traceback with a matching filename
        try:
            exec(compile("raise ValueError('from src')", "src/fake_module.py", "exec"))
        except ValueError as e:
            files = pusher._guess_relevant_files(e)
            assert any("src/" in f for f in files)

    @patch("sync.log_pusher.subprocess.run")
    def test_report_error_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(stdout="ok\n", returncode=0)

        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        try:
            raise RuntimeError("test failure")
        except RuntimeError as e:
            branch = pusher.report_error(e, context={"phase": "test"})

        assert branch is not None
        assert branch.startswith("error-report/err_")

        # Check report file was written
        report_files = list((tmp_path / "error_reports").glob("err_*.json"))
        assert len(report_files) == 1

        report = json.loads(report_files[0].read_text())
        assert report["error"]["type"] == "RuntimeError"
        assert report["context"]["phase"] == "test"

    @patch("sync.log_pusher.subprocess.run")
    def test_report_error_push_failure(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git push")

        pusher = ErrorLogPusher(repo_dir=str(tmp_path))
        try:
            raise RuntimeError("test failure")
        except RuntimeError as e:
            branch = pusher.report_error(e)

        assert branch is None
