"""Tests for src/display/dashboard.py"""

import pytest

from display.dashboard import Dashboard


class TestDashboard:
    def test_init(self):
        dash = Dashboard()
        assert dash.host == "0.0.0.0"
        assert dash.port == 8080

    def test_init_custom(self):
        dash = Dashboard(host="127.0.0.1", port=3000)
        assert dash.host == "127.0.0.1"
        assert dash.port == 3000

    def test_start_not_implemented(self):
        dash = Dashboard()
        with pytest.raises(NotImplementedError):
            dash.start()
