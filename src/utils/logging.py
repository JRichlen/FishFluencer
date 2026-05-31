"""Structured logging setup."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
