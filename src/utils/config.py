"""YAML config loader with ${ENV_VAR} interpolation."""

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            name = match.group(1)
            return os.environ.get(name, "")
        return _ENV_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


def load_config(path: str | Path) -> dict:
    """Load a YAML config file and interpolate ${ENV_VAR} placeholders."""
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return _interpolate(raw)


def load_fish_profiles(path: str | Path) -> dict:
    """Load fish_profiles.yaml. Returns the top-level mapping."""
    with open(path) as f:
        return yaml.safe_load(f) or {}
