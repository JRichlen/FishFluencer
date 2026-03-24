"""Tests for src/utils/config.py"""

import os

import pytest

from utils.config import _resolve_env_vars, load_config, load_dotenv


class TestLoadDotenv:
    def test_loads_key_value(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_TEST_VAR=hello\n")
        monkeypatch.delenv("MY_TEST_VAR", raising=False)

        load_dotenv(str(env_file))

        assert os.environ["MY_TEST_VAR"] == "hello"
        monkeypatch.delenv("MY_TEST_VAR", raising=False)

    def test_skips_comments_and_blanks(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nVALID_VAR=yes\n")
        monkeypatch.delenv("VALID_VAR", raising=False)

        load_dotenv(str(env_file))

        assert os.environ["VALID_VAR"] == "yes"
        monkeypatch.delenv("VALID_VAR", raising=False)

    def test_strips_double_quotes(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text('QUOTED_VAR="some value"\n')
        monkeypatch.delenv("QUOTED_VAR", raising=False)

        load_dotenv(str(env_file))

        assert os.environ["QUOTED_VAR"] == "some value"
        monkeypatch.delenv("QUOTED_VAR", raising=False)

    def test_strips_single_quotes(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("SQ_VAR='single quoted'\n")
        monkeypatch.delenv("SQ_VAR", raising=False)

        load_dotenv(str(env_file))

        assert os.environ["SQ_VAR"] == "single quoted"
        monkeypatch.delenv("SQ_VAR", raising=False)

    def test_does_not_override_existing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EXISTING_VAR", "original")
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR=overridden\n")

        load_dotenv(str(env_file))

        assert os.environ["EXISTING_VAR"] == "original"

    def test_missing_file_is_noop(self):
        load_dotenv("/nonexistent/.env")

    def test_skips_lines_without_equals(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("NOEQ\nGOOD=val\n")
        monkeypatch.delenv("GOOD", raising=False)

        load_dotenv(str(env_file))

        assert os.environ.get("NOEQ") is None
        assert os.environ["GOOD"] == "val"
        monkeypatch.delenv("GOOD", raising=False)


class TestResolveEnvVars:
    def test_plain_string(self):
        assert _resolve_env_vars("hello") == "hello"

    def test_env_var_replacement(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "secret123")
        assert _resolve_env_vars("${TEST_KEY}") == "secret123"

    def test_env_var_missing_keeps_original(self):
        # Ensure this env var doesn't exist
        os.environ.pop("NONEXISTENT_VAR_XYZ", None)
        assert _resolve_env_vars("${NONEXISTENT_VAR_XYZ}") == "${NONEXISTENT_VAR_XYZ}"

    def test_partial_env_var_in_string(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "world")
        assert _resolve_env_vars("hello ${MY_VAR}!") == "hello world!"

    def test_dict_resolution(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        result = _resolve_env_vars({"host": "${DB_HOST}", "port": 5432})
        assert result["host"] == "localhost"
        assert result["port"] == 5432

    def test_list_resolution(self, monkeypatch):
        monkeypatch.setenv("ITEM", "value")
        result = _resolve_env_vars(["${ITEM}", "static"])
        assert result == ["value", "static"]

    def test_non_string_passthrough(self):
        assert _resolve_env_vars(42) == 42
        assert _resolve_env_vars(None) is None
        assert _resolve_env_vars(True) is True


class TestLoadConfig:
    def test_load_existing_config(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value\nnested:\n  a: 1\n")

        config = load_config(str(config_file))
        assert config["key"] == "value"
        assert config["nested"]["a"] == 1

    def test_load_missing_config(self):
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("/nonexistent/path.yaml")

    def test_load_with_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_API_KEY", "sk-test-123")
        config_file = tmp_path / "test.yaml"
        config_file.write_text('api_key: "${MY_API_KEY}"\n')

        config = load_config(str(config_file))
        assert config["api_key"] == "sk-test-123"

    def test_load_config_reads_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DOTENV_TEST_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("DOTENV_TEST_KEY=from-dotenv\n")
        config_file = tmp_path / "test.yaml"
        config_file.write_text('val: "${DOTENV_TEST_KEY}"\n')

        config = load_config(str(config_file))
        assert config["val"] == "from-dotenv"
        monkeypatch.delenv("DOTENV_TEST_KEY", raising=False)

    def test_load_config_env_overrides_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PRIORITY_KEY", "from-env")
        env_file = tmp_path / ".env"
        env_file.write_text("PRIORITY_KEY=from-dotenv\n")
        config_file = tmp_path / "test.yaml"
        config_file.write_text('val: "${PRIORITY_KEY}"\n')

        config = load_config(str(config_file))
        assert config["val"] == "from-env"
