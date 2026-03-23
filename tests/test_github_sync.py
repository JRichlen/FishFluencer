"""Tests for src/sync/github_sync.py"""

import subprocess
from unittest.mock import MagicMock, patch

from sync.github_sync import GitHubSyncAgent


class TestGitHubSyncAgent:
    def test_init_defaults(self):
        agent = GitHubSyncAgent()
        assert str(agent.repo_dir) == "/opt/fishfluencer"
        assert agent.branch == "main"
        assert agent.service_name == "fishfluencer.service"

    @patch("sync.github_sync.subprocess.run")
    def test_sync_no_changes(self, mock_run):
        mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)

        agent = GitHubSyncAgent()
        result = agent.sync()

        assert result["changed"] is False
        assert result["restarted"] is False
        assert result["error"] is None

    @patch("sync.github_sync.subprocess.run")
    def test_sync_with_changes(self, mock_run):
        call_count = [0]
        hashes = ["old_hash\n", "old_hash\n", "pulled\n", "new_hash\n"]

        def side_effect(*args, **kwargs):
            result = MagicMock()
            result.stdout = hashes[min(call_count[0], len(hashes) - 1)]
            result.returncode = 0
            call_count[0] += 1
            return result

        mock_run.side_effect = side_effect

        agent = GitHubSyncAgent(post_update_script=None)
        result = agent.sync()

        assert result["changed"] is True
        assert result["restarted"] is True

    @patch("sync.github_sync.subprocess.run")
    def test_sync_with_post_update_script(self, mock_run, tmp_path):
        script = tmp_path / "scripts" / "install_deps.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho ok")

        call_count = [0]

        def side_effect(*args, **kwargs):
            result = MagicMock()
            if call_count[0] == 0:
                result.stdout = "old_hash\n"
            elif call_count[0] == 3:
                result.stdout = "new_hash\n"
            else:
                result.stdout = "ok\n"
            result.returncode = 0
            call_count[0] += 1
            return result

        mock_run.side_effect = side_effect

        agent = GitHubSyncAgent(
            repo_dir=str(tmp_path),
            post_update_script="scripts/install_deps.sh",
        )
        result = agent.sync()
        assert result["changed"] is True

    @patch("sync.github_sync.subprocess.run")
    def test_sync_command_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        agent = GitHubSyncAgent()
        result = agent.sync()
        assert result["error"] is not None

    @patch("sync.github_sync.subprocess.run")
    def test_sync_generic_error(self, mock_run):
        mock_run.side_effect = OSError("network error")

        agent = GitHubSyncAgent()
        result = agent.sync()
        assert "network error" in result["error"]

    @patch("sync.github_sync.subprocess.run")
    def test_get_head_hash(self, mock_run):
        mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)
        agent = GitHubSyncAgent()
        assert agent._get_head_hash() == "abc123"
