"""Tests for src/data/db.py"""

import time

import pytest

from capture.temperature import TempReading
from data.db import FishDB
from inference.behavior import Behavior, BehaviorEvent


@pytest.fixture
def db(tmp_path):
    return FishDB(db_path=str(tmp_path / "test.db"))


class TestFishDB:
    def test_init_creates_db(self, tmp_path):
        db_path = tmp_path / "sub" / "test.db"
        FishDB(db_path=str(db_path))
        assert db_path.exists()

    def test_log_behavior(self, db):
        event = BehaviorEvent(
            fish_id=0, fish_label="fish", behavior=Behavior.CRUISING,
            confidence=0.8, zone="midwater", duration_frames=50,
            description="cruising along",
        )
        db.log_behavior(event)
        summary = db.get_behavior_summary(hours=1.0)
        assert len(summary) == 1
        assert summary[0]["behavior"] == "cruising"

    def test_log_temperature(self, db):
        reading = TempReading(
            celsius=23.0, fahrenheit=73.4, timestamp=time.time(), sensor_id="28-abc"
        )
        db.log_temperature(reading)
        temps = db.get_recent_temps(hours=1.0)
        assert len(temps) == 1
        assert temps[0]["readings"] == 1
        assert temps[0]["avg_f"] == pytest.approx(73.4)

    def test_register_and_get_snapshot(self, db):
        db.register_snapshot("/tmp/snap.jpg", "A fish swimming", purge_hours=0.0)
        # purge_hours=0.0 means it's immediately purgeable
        time.sleep(0.01)
        purgeable = db.get_purgeable_snapshots()
        assert len(purgeable) >= 1
        assert purgeable[0]["filepath"] == "/tmp/snap.jpg"

    def test_delete_snapshot_record(self, db):
        db.register_snapshot("/tmp/snap.jpg", "A fish", purge_hours=0.0)
        time.sleep(0.01)
        purgeable = db.get_purgeable_snapshots()
        db.delete_snapshot_record(purgeable[0]["id"])
        assert db.get_purgeable_snapshots() == []

    def test_get_behavior_summary_empty(self, db):
        summary = db.get_behavior_summary(hours=1.0)
        assert summary == []

    def test_get_recent_temps_empty(self, db):
        temps = db.get_recent_temps(hours=1.0)
        assert len(temps) == 1
        assert temps[0]["readings"] == 0

    def test_log_post(self, db):
        db.log_post("twitter", "Hello from Jordan!", "summary text")
        with db._conn() as conn:
            rows = conn.execute("SELECT * FROM posts").fetchall()
            assert len(rows) == 1
            assert dict(rows[0])["platform"] == "twitter"
            assert dict(rows[0])["content"] == "Hello from Jordan!"

    def test_snapshot_not_purgeable_when_future(self, db):
        db.register_snapshot("/tmp/future.jpg", "A fish", purge_hours=24.0)
        purgeable = db.get_purgeable_snapshots()
        assert purgeable == []
