"""Tests for src/utils/log.py"""

import logging

from utils.log import setup_logging


class TestSetupLogging:
    def test_sets_level(self):
        setup_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_default_info_level(self):
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_suppresses_noisy_loggers(self):
        setup_logging()
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
