"""
SQLite database for behavior logs, temperature readings, and post history.
All data stays on-device.
"""

import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS behavior_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    fish_id INTEGER NOT NULL,
    fish_label TEXT NOT NULL,
    behavior TEXT NOT NULL,
    zone TEXT NOT NULL,
    confidence REAL NOT NULL,
    description TEXT NOT NULL,
    duration_frames INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS temperature_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    celsius REAL NOT NULL,
    fahrenheit REAL NOT NULL,
    sensor_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    filepath TEXT NOT NULL,
    description TEXT,
    purge_after REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    summary_used TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_behavior_ts ON behavior_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_temp_ts ON temperature_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_snap_purge ON snapshots(purge_after);
"""


class FishDB:
    def __init__(self, db_path: str = "data/fishfluencer.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- Writes ---

    def log_behavior(self, event) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO behavior_log
                   (timestamp, fish_id, fish_label, behavior, zone,
                    confidence, description, duration_frames)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(), event.fish_id, event.fish_label,
                    event.behavior.value, event.zone, event.confidence,
                    event.description, event.duration_frames,
                ),
            )

    def log_temperature(self, reading) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO temperature_log
                   (timestamp, celsius, fahrenheit, sensor_id)
                   VALUES (?, ?, ?, ?)""",
                (reading.timestamp, reading.celsius,
                 reading.fahrenheit, reading.sensor_id),
            )

    def register_snapshot(
        self, filepath: str, description: str, purge_hours: float = 24.0
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO snapshots
                   (timestamp, filepath, description, purge_after)
                   VALUES (?, ?, ?, ?)""",
                (time.time(), filepath, description,
                 time.time() + purge_hours * 3600),
            )

    def log_post(self, platform: str, content: str, summary: str,
                 status: str = "posted") -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO posts
                   (timestamp, platform, content, summary_used, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (time.time(), platform, content, summary, status),
            )

    # --- Reads ---

    def get_purgeable_snapshots(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, filepath FROM snapshots WHERE purge_after < ?",
                (time.time(),),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_snapshot_record(self, snap_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM snapshots WHERE id = ?", (snap_id,))

    def get_behavior_summary(self, hours: float = 12.0) -> List[dict]:
        since = time.time() - hours * 3600
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT fish_label, behavior, zone, description,
                          COUNT(*) AS event_count,
                          AVG(confidence) AS avg_confidence
                   FROM behavior_log
                   WHERE timestamp > ?
                   GROUP BY fish_label, behavior
                   ORDER BY event_count DESC""",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_temps(self, hours: float = 12.0) -> List[dict]:
        since = time.time() - hours * 3600
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT AVG(fahrenheit) AS avg_f, MIN(fahrenheit) AS min_f,
                          MAX(fahrenheit) AS max_f, COUNT(*) AS readings
                   FROM temperature_log WHERE timestamp > ?""",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_posts(self, limit: int = 10) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT timestamp, platform, content, status
                   FROM posts ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_dashboard_stats(self) -> dict:
        with self._conn() as conn:
            last_temp = conn.execute(
                "SELECT fahrenheit, timestamp FROM temperature_log "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            behaviors_24h = conn.execute(
                "SELECT COUNT(*) AS c FROM behavior_log WHERE timestamp > ?",
                (time.time() - 86400,),
            ).fetchone()
            posts_total = conn.execute(
                "SELECT COUNT(*) AS c FROM posts"
            ).fetchone()
            snapshots_current = conn.execute(
                "SELECT COUNT(*) AS c FROM snapshots WHERE purge_after > ?",
                (time.time(),),
            ).fetchone()
        return {
            "last_temp_f": last_temp["fahrenheit"] if last_temp else None,
            "last_temp_at": last_temp["timestamp"] if last_temp else None,
            "behaviors_24h": behaviors_24h["c"] if behaviors_24h else 0,
            "posts_total": posts_total["c"] if posts_total else 0,
            "snapshots_current": snapshots_current["c"] if snapshots_current else 0,
        }
