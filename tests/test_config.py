"""Tests for src/utils/config.py"""

import os

import pytest

from utils.config import _resolve_env_vars, load_config


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
