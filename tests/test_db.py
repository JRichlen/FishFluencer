"""SQLite schema, write/read roundtrip, and legacy column migration."""

import sqlite3
import time
from dataclasses import dataclass

from src.capture.temperature import TempReading
from src.data.db import FishDB
from src.inference.behavior import Behavior


@dataclass
class FakeEvent:
    subject_id: int
    subject_label: str
    behavior: Behavior
    zone: str
    confidence: float
    description: str
    duration_frames: int


def test_schema_init(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    assert db.get_behavior_summary(hours=1.0) == []
    assert db.get_recent_posts() == []


def test_log_and_summarize_behavior(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    for _ in range(3):
        db.log_behavior(
            FakeEvent(
                subject_id=0, subject_label="betta",
                behavior=Behavior.DARTING, zone="midwater",
                confidence=0.9, description="darting around",
                duration_frames=30,
            )
        )
    summary = db.get_behavior_summary(hours=1.0)
    assert len(summary) == 1
    assert summary[0]["subject_label"] == "betta"
    assert summary[0]["event_count"] == 3
    assert summary[0]["behavior"] == "darting"


def test_temperature_roundtrip(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_temperature(
        TempReading(
            celsius=22.5, fahrenheit=72.5,
            timestamp=time.time(), sensor_id="28-test",
        )
    )
    temps = db.get_recent_temps(hours=1.0)
    assert temps[0]["readings"] == 1
    assert 72.0 < temps[0]["avg_f"] < 73.0


def test_post_log(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_post("twitter", "blub blub", "summary text", status="posted")
    posts = db.get_recent_posts()
    assert len(posts) == 1
    assert posts[0]["platform"] == "twitter"
    assert posts[0]["status"] == "posted"


def test_dashboard_stats(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_temperature(
        TempReading(
            celsius=22.0, fahrenheit=71.6,
            timestamp=time.time(), sensor_id="28-test",
        )
    )
    stats = db.get_dashboard_stats()
    assert stats["last_temp_f"] is not None
    assert stats["posts_total"] == 0


def test_legacy_fish_columns_get_migrated(tmp_path):
    """A pre-existing database with the old `fish_id`/`fish_label`
    columns should be transparently renamed to `subject_id` /
    `subject_label` on open."""
    db_path = tmp_path / "legacy.db"

    # Build a legacy schema by hand and stick a row in it.
    legacy_conn = sqlite3.connect(str(db_path))
    legacy_conn.executescript(
        """
        CREATE TABLE behavior_log (
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
        """
    )
    legacy_conn.execute(
        "INSERT INTO behavior_log (timestamp, fish_id, fish_label, behavior, "
        "zone, confidence, description, duration_frames) VALUES "
        "(?, 0, 'betta', 'darting', 'midwater', 0.9, 'pre-migration row', 30)",
        (time.time(),),
    )
    legacy_conn.commit()
    legacy_conn.close()

    # Open through FishDB — should trigger the migration silently.
    db = FishDB(str(db_path))

    cols = {
        row[1]
        for row in sqlite3.connect(str(db_path))
        .execute("PRAGMA table_info(behavior_log)")
        .fetchall()
    }
    assert "subject_id" in cols
    assert "subject_label" in cols
    assert "fish_id" not in cols
    assert "fish_label" not in cols

    # The pre-existing row survives the rename.
    summary = db.get_behavior_summary(hours=1.0)
    assert summary[0]["subject_label"] == "betta"
    assert summary[0]["description"] == "pre-migration row"
