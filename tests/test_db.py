"""SQLite schema and write/read roundtrip."""

import time
from dataclasses import dataclass

from src.capture.temperature import TempReading
from src.data.db import FishDB
from src.inference.behavior import Behavior


@dataclass
class FakeEvent:
    fish_id: int
    fish_label: str
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
                fish_id=0, fish_label="betta",
                behavior=Behavior.DARTING, zone="midwater",
                confidence=0.9, description="darting around",
                duration_frames=30,
            )
        )
    summary = db.get_behavior_summary(hours=1.0)
    assert len(summary) == 1
    assert summary[0]["fish_label"] == "betta"
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
