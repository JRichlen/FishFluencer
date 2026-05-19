"""Summarizer — verify the text reflects profile, temp, and mode."""

import time
from dataclasses import dataclass

from src.capture.temperature import TempReading
from src.data.db import FishDB
from src.data.summarizer import BehaviorSummarizer
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


def test_fish_mode_summary(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_behavior(
        FakeEvent(
            subject_id=0, subject_label="betta",
            behavior=Behavior.GLASS_SURFING, zone="midwater",
            confidence=0.85, description="surfing the left wall",
            duration_frames=60,
        )
    )
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
    assert "75.2" in summary
    assert "glass_surfing" in summary


def test_dog_mode_summary(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_behavior(
        FakeEvent(
            subject_id=0, subject_label="dog",
            behavior=Behavior.PACING, zone="middle",
            confidence=0.78, description="pacing at the kennel door",
            duration_frames=120,
        )
    )
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
