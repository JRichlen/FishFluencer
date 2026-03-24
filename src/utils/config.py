"""YAML config loader with environment variable overrides."""

import logging
import os
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

ENV_PATTERN = re.compile(r"\$\{(\w+)\}")


def load_dotenv(env_path: str = ".env") -> None:
    """Load variables from a .env file into os.environ.

    Supports KEY=value, KEY="value", and KEY='value' formats.
    Skips blank lines and comments (lines starting with #).
    Does not override variables that are already set.
    """
    path = Path(env_path)
    if not path.is_file():
        return

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Strip matching quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            if key and key not in os.environ:
                os.environ[key] = value
                logger.debug("Loaded env var from .env: %s", key)


def _resolve_env_vars(value):
    """Replace ${VAR_NAME} patterns with environment variable values."""
    if isinstance(value, str):
        match = ENV_PATTERN.fullmatch(value)
        if match:
            env_var = match.group(1)
            return os.environ.get(env_var, value)
        return ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_config(config_path: str = "config/default.yaml") -> dict:
    """Load YAML config and resolve environment variable references.

    Automatically loads a .env file from the project root (if present)
    before resolving variables. This supports local development without
    requiring manual ``export`` commands. Variables already set in the
    real environment (e.g. via systemd EnvironmentFile) take precedence.
    """
    # Load .env relative to the config file's parent directory
    config_dir = Path(config_path).resolve().parent
    for candidate in [config_dir / ".env", config_dir.parent / ".env"]:
        if candidate.is_file():
            load_dotenv(str(candidate))
            logger.debug("Loaded .env from %s", candidate)
            break

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    resolved = _resolve_env_vars(config)
    logger.info("Config loaded from %s", config_path)
    return resolved
