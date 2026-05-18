"""Summarizer — text output should reference fish profile and behaviors."""

import time
from dataclasses import dataclass

from src.capture.temperature import TempReading
from src.data.db import FishDB
from src.data.summarizer import BehaviorSummarizer
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


def test_summary_includes_profile_and_temp(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    db.log_behavior(
        FakeEvent(
            fish_id=0, fish_label="betta",
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
    summary = BehaviorSummarizer(db, profiles).generate_summary(hours=1.0)

    assert "Sir Bubbles" in summary
    assert "betta" in summary
    assert "75.2" in summary
    assert "glass_surfing" in summary
    assert "surfing the left wall" in summary


def test_empty_period(tmp_path):
    db = FishDB(str(tmp_path / "test.db"))
    summary = BehaviorSummarizer(db, {}).generate_summary(hours=1.0)
    assert "No fish activity detected" in summary
