"""Local HTTP dashboard served on the 7" HDMI display.

Read-only — shows current temperature, recent posts, behavior counts,
and image storage usage. Bound to localhost by default; a kiosk-mode
browser on the Coral points at it.
"""

import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string

logger = logging.getLogger(__name__)

INDEX_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "dashboard" / "templates" / "index.html"
)


class Dashboard:
    def __init__(self, db, host: str = "127.0.0.1", port: int = 8080):
        self.db = db
        self.host = host
        self.port = port
        self._app = Flask(__name__)
        self._thread: threading.Thread | None = None
        self._register_routes()

    def _register_routes(self):
        @self._app.route("/")
        def index():
            template = INDEX_TEMPLATE_PATH.read_text()
            return render_template_string(template)

        @self._app.route("/api/stats")
        def stats():
            data = self.db.get_dashboard_stats()
            data["last_temp_at_human"] = (
                datetime.fromtimestamp(data["last_temp_at"]).strftime("%H:%M:%S")
                if data.get("last_temp_at") else None
            )
            return jsonify(data)

        @self._app.route("/api/posts")
        def posts():
            rows = self.db.get_recent_posts(limit=10)
            for r in rows:
                r["timestamp_human"] = (
                    datetime.fromtimestamp(r["timestamp"]).strftime("%b %d %H:%M")
                )
            return jsonify(rows)

    def start(self) -> None:
        """Start the dashboard in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return

        def _run():
            try:
                self._app.run(
                    host=self.host,
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                )
            except Exception as e:
                logger.error("Dashboard server stopped: %s", e)

        self._thread = threading.Thread(target=_run, daemon=True, name="dashboard")
        self._thread.start()
        logger.info("Dashboard listening on http://%s:%d", self.host, self.port)
