"""HDMI local dashboard (placeholder for Flask/PyGame)."""

import logging

logger = logging.getLogger(__name__)


class Dashboard:
    """Local HDMI dashboard for tank status display."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port

    def start(self):
        logger.info("Dashboard available at http://%s:%d", self.host, self.port)
        raise NotImplementedError("Dashboard UI integration pending")
