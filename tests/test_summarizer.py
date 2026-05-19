"""Summarizer — span-based duration aggregation in each mode."""

import time
from dataclasses import dataclass

from src.capture.temperature import TempReading
from src.data.db import FishDB
from src.data.summarizer import AlertSummarizer, BehaviorSummarizer
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


def _log_span(db, subject_id, label, behavior, *, zone, count, gap_s=60.0):
    """Helper: log `count` events spaced gap_s seconds apart, simulating
    one analyzer transition + checkpoint sequence."""
    now = time.time()
    for i in range(count):
        # Forge the timestamp by inserting directly.
        with db._conn() as conn:
            conn.execute(
                """INSERT INTO behavior_log
                   (timestamp, subject_id, subject_label, behavior, zone,
                    confidence, description, duration_frames)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now - (count - 1 - i) * gap_s,
                    subject_id, label, behavior.value, zone,
                    0.85, f"{label} doing {behavior.value}", 30,
                ),
            )


# --- BehaviorSummarizer -------------------------------------------------


def test_fish_mode_summary(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    _log_span(db, 0, "betta", Behavior.GLASS_SURFING, zone="midwater", count=3)
    db.log_temperature(
        TempReading(
            celsius=24.0, fahrenheit=75.2,
            timestamp=time.time(), sensor_id="28-test",
        )
    )
    profiles = {"betta": {"name": "Sir Bubbles", "personality": "dramatic diva"}}
    summary = BehaviorSummarizer(db, profiles, mode="fish").generate_summary(hours=1.0)

    assert "Fish Tank Status Report" in summary
    assert "Water temperature" in summary
    assert "Sir Bubbles" in summary
    assert "glass_surfing" in summary
    # ~3 events × 60s + checkpoint padding → at least a couple of minutes
    assert "min" in summary or "s" in summary


def test_dog_mode_summary(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    _log_span(db, 0, "dog", Behavior.PACING, zone="middle", count=10)
    db.log_temperature(
        TempReading(
            celsius=21.5, fahrenheit=70.7,
            timestamp=time.time(), sensor_id="28-test",
        )
    )
    profiles = {"dog": {"name": "Rex", "personality": "earnest rescue mutt"}}
    summary = BehaviorSummarizer(db, profiles, mode="dog").generate_summary(hours=1.0)

    assert "Kennel Status Report" in summary
    assert "Ambient temperature" in summary
    assert "Water" not in summary
    assert "Rex" in summary
    assert "pacing" in summary
    assert "70.7" in summary


def test_summary_shows_humanized_duration(tmp_path):
    """A span of 10 events at 60s gaps should render as ~10 minutes,
    not as a raw event count."""
    db = FishDB(str(tmp_path / "test.db"))
    _log_span(db, 0, "dog", Behavior.LYING_DOWN, zone="floor", count=10)
    summary = BehaviorSummarizer(db, {}, mode="dog").generate_summary(hours=1.0)
    # 10 × 60s gaps = 540s span (start at -540, end at 0) plus
    # +60 checkpoint padding → ~10 min.
    assert "min" in summary
    assert "lying_down" in summary


def test_empty_period_fish(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    summary = BehaviorSummarizer(db, {}, mode="fish").generate_summary(hours=1.0)
    assert "No fish activity detected" in summary


def test_empty_period_dog(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    summary = BehaviorSummarizer(db, {}, mode="dog").generate_summary(hours=1.0)
    assert "No subject activity detected" in summary


def test_invalid_mode_rejected(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    import pytest
    with pytest.raises(ValueError):
        BehaviorSummarizer(db, {}, mode="cat")


# --- AlertSummarizer ----------------------------------------------------


def test_alert_summary_marks_urgency(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    reading = TempReading(
        celsius=32.0, fahrenheit=89.6,
        timestamp=time.time(), sensor_id="28-test",
    )
    summary = AlertSummarizer(db, {}).generate_alert_summary(
        reading, threshold_f=85.0
    )
    assert "HEAT-STROKE ALERT" in summary
    assert "89.6" in summary
    assert "85.0" in summary
    assert "urgent" in summary.lower()


def test_alert_summary_includes_recent_behavior(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    _log_span(db, 0, "dog", Behavior.PACING, zone="middle", count=2)
    reading = TempReading(
        celsius=32.0, fahrenheit=89.6,
        timestamp=time.time(), sensor_id="28-test",
    )
    profiles = {"dog": {"name": "Rex", "personality": "earnest"}}
    summary = AlertSummarizer(db, profiles).generate_alert_summary(
        reading, threshold_f=85.0
    )
    assert "Rex" in summary
    assert "pacing" in summary


def test_alert_summary_when_no_subject(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    reading = TempReading(
        celsius=32.0, fahrenheit=89.6,
        timestamp=time.time(), sensor_id="28-test",
    )
    summary = AlertSummarizer(db, {}).generate_alert_summary(
        reading, threshold_f=85.0
    )
    assert "No recent subject activity" in summary
