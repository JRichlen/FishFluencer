"""YAML config loader with environment variable overrides."""

import os
import re
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

ENV_PATTERN = re.compile(r"\$\{(\w+)\}")


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
    """Load YAML config and resolve environment variable references."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    resolved = _resolve_env_vars(config)
    logger.info("Config loaded from %s", config_path)
    return resolved
