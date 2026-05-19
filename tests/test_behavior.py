"""Behavior analyzer — classify based on trajectory shape and mode."""

from dataclasses import dataclass, field
from typing import List, Tuple

import pytest

from src.inference.behavior import Behavior, BehaviorAnalyzer


@dataclass
class FakeSubject:
    """Mimics a TrackedSubject for the analyzer's input contract."""

    subject_id: int
    label: str
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    frames_tracked: int = 30
    frames_missing: int = 0


def linear_trajectory(start, step, count):
    x, y = start
    dx, dy = step
    return [(x + dx * i, y + dy * i) for i in range(count)]


# --- Fish-mode rules ----------------------------------------------------


def test_resting_fish():
    analyzer = BehaviorAnalyzer(resting_speed_threshold=2.0, mode="fish")
    sub = FakeSubject(
        subject_id=0, label="fish", center=(960, 900),
        bbox=(900, 840, 1020, 960),
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.RESTING
    assert events[0].zone == "bottom"
    assert "tank" in events[0].description


def test_darting_fish():
    analyzer = BehaviorAnalyzer(darting_speed_threshold=40.0, mode="fish")
    sub = FakeSubject(
        subject_id=1, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((100, 500), (60, 0), 30),
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.DARTING
    assert "dart" in events[0].description.lower()


def test_glass_surfing_fish():
    analyzer = BehaviorAnalyzer(
        glass_surf_edge_margin=80, frame_width=1920, mode="fish"
    )
    traj = [(40, 500 + i) for i in range(30)]
    sub = FakeSubject(
        subject_id=2, label="fish", center=traj[-1],
        bbox=(20, traj[-1][1] - 20, 60, traj[-1][1] + 20),
        trajectory=traj,
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.GLASS_SURFING


def test_skip_short_tracks():
    analyzer = BehaviorAnalyzer(min_behavior_frames=10, mode="fish")
    sub = FakeSubject(
        subject_id=3, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=[(500, 500)],
        frames_tracked=5,
    )
    assert analyzer.analyze([sub]) == []


# --- Dog-mode rules -----------------------------------------------------


def test_pacing_dog():
    """Same physics as glass-surfing, but labeled `pacing` and described
    as a stress indicator in dog mode."""
    analyzer = BehaviorAnalyzer(
        glass_surf_edge_margin=80, frame_width=1920, mode="dog"
    )
    traj = [(40, 500 + i) for i in range(30)]
    sub = FakeSubject(
        subject_id=0, label="dog", center=traj[-1],
        bbox=(20, traj[-1][1] - 20, 60, traj[-1][1] + 20),
        trajectory=traj,
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.PACING
    assert "stress" in events[0].description.lower()
    assert "kennel" in events[0].description.lower()


def test_running_dog():
    """Sudden burst should be DARTING with the dog-mode verb 'run'."""
    analyzer = BehaviorAnalyzer(darting_speed_threshold=40.0, mode="dog")
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((100, 500), (60, 0), 30),
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.DARTING
    assert "run" in events[0].description.lower()
    assert "kennel" in events[0].description.lower()


def test_dog_uses_dog_zones():
    """Dog mode swaps surface/midwater/bottom for upper/middle/floor."""
    analyzer = BehaviorAnalyzer(mode="dog", frame_height=1080)
    sub = FakeSubject(
        subject_id=0, label="dog", center=(960, 900),  # in lower third
        bbox=(900, 840, 1020, 960),
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    events = analyzer.analyze([sub])
    assert events[0].zone == "floor"


def test_dog_mode_skips_surface_breathing():
    """No SURFACE_BREATHING in dog mode — a still dog at the top of frame
    should be RESTING, not SURFACE_BREATHING (which doesn't apply)."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0, mode="dog", frame_height=1080
    )
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 100),  # upper third
        bbox=(450, 50, 550, 150),
        trajectory=linear_trajectory((500, 100), (0, 0), 30),
    )
    events = analyzer.analyze([sub])
    assert events[0].behavior == Behavior.RESTING
    assert events[0].zone == "upper"


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        BehaviorAnalyzer(mode="goldfish-but-with-extra-steps")
