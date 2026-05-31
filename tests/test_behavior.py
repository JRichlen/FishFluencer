"""Behavior analyzer — classification rules, posture, and span emission."""

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
    events = analyzer.analyze([sub], now_ts=0.0)
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
    events = analyzer.analyze([sub], now_ts=0.0)
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
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.GLASS_SURFING


def test_skip_short_tracks():
    analyzer = BehaviorAnalyzer(min_behavior_frames=10, mode="fish")
    sub = FakeSubject(
        subject_id=3, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=[(500, 500)],
        frames_tracked=5,
    )
    assert analyzer.analyze([sub], now_ts=0.0) == []


# --- Dog-mode rules -----------------------------------------------------


def test_pacing_dog():
    analyzer = BehaviorAnalyzer(
        glass_surf_edge_margin=80, frame_width=1920, mode="dog"
    )
    traj = [(40, 500 + i) for i in range(30)]
    sub = FakeSubject(
        subject_id=0, label="dog", center=traj[-1],
        bbox=(20, traj[-1][1] - 20, 60, traj[-1][1] + 20),
        trajectory=traj,
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.PACING
    assert "stress" in events[0].description.lower()


def test_running_dog():
    analyzer = BehaviorAnalyzer(darting_speed_threshold=40.0, mode="dog")
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((100, 500), (60, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.DARTING
    assert "run" in events[0].description.lower()
    assert "kennel" in events[0].description.lower()


def test_dog_uses_dog_zones():
    analyzer = BehaviorAnalyzer(mode="dog", frame_height=1080)
    # A wide, lying-down bbox in the lower third.
    sub = FakeSubject(
        subject_id=0, label="dog", center=(960, 900),
        bbox=(800, 850, 1120, 950),  # 320×100 — definitely lying
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].zone == "floor"


# --- Tier 2 posture detection ------------------------------------------


def test_lying_down_detected_from_wide_bbox():
    """Side-mounted camera + still dog + wide bbox (W/H ≥ 1.4) → LYING_DOWN."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        posture_aspect_lying=1.4,
        mode="dog",
        frame_height=1080,
    )
    # bbox 200 wide × 100 tall → aspect 2.0 → LYING_DOWN
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 900),
        bbox=(400, 850, 600, 950),
        trajectory=linear_trajectory((500, 900), (0, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.LYING_DOWN
    assert "lying" in events[0].description.lower()


def test_sitting_detected_from_square_bbox():
    """Still dog with a roughly square bbox → SITTING."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        posture_aspect_lying=1.4,
        posture_aspect_sitting=0.9,
        mode="dog",
    )
    # bbox 100 wide × 100 tall → aspect 1.0 → SITTING
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((500, 500), (0, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.SITTING


def test_standing_detected_from_tall_bbox():
    """Still dog with a tall bbox (W/H ≤ 0.9) → STANDING."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        posture_aspect_sitting=0.9,
        mode="dog",
    )
    # bbox 60 wide × 100 tall → aspect 0.6 → STANDING
    sub = FakeSubject(
        subject_id=0, label="dog", center=(500, 500),
        bbox=(470, 450, 530, 550),
        trajectory=linear_trajectory((500, 500), (0, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.STANDING


def test_fish_mode_does_not_use_posture():
    """Posture classification is gated to dog mode — fish stay RESTING."""
    analyzer = BehaviorAnalyzer(resting_speed_threshold=2.0, mode="fish")
    sub = FakeSubject(
        subject_id=0, label="fish", center=(500, 900),
        bbox=(400, 850, 600, 950),  # wide bbox, would be LYING_DOWN in dog mode
        trajectory=linear_trajectory((500, 900), (0, 0), 30),
    )
    events = analyzer.analyze([sub], now_ts=0.0)
    assert events[0].behavior == Behavior.RESTING


# --- Tier 2 span emission ---------------------------------------------


def test_does_not_re_emit_same_behavior_within_checkpoint():
    """Two consecutive analyses with the same behavior within the
    checkpoint window should emit only on the first one."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        checkpoint_interval_seconds=60.0,
        mode="fish",
    )
    sub = FakeSubject(
        subject_id=0, label="fish", center=(960, 900),
        bbox=(900, 840, 1020, 960),
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    first = analyzer.analyze([sub], now_ts=0.0)
    assert len(first) == 1
    # Same subject, same behavior, 30 seconds later → no new event.
    second = analyzer.analyze([sub], now_ts=30.0)
    assert second == []


def test_emits_on_behavior_change():
    """When the classification changes, a new event is emitted
    immediately even if the checkpoint interval hasn't elapsed."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        darting_speed_threshold=40.0,
        checkpoint_interval_seconds=60.0,
        mode="fish",
    )
    # First: resting.
    resting = FakeSubject(
        subject_id=0, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((500, 500), (0, 0), 30),
    )
    analyzer.analyze([resting], now_ts=0.0)
    # Second: darting (same subject_id) — must emit.
    darting = FakeSubject(
        subject_id=0, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((100, 500), (60, 0), 30),
    )
    events = analyzer.analyze([darting], now_ts=5.0)
    assert len(events) == 1
    assert events[0].behavior == Behavior.DARTING


def test_re_emits_after_checkpoint_interval():
    """A sustained behavior should re-emit once the checkpoint interval
    elapses, so the summarizer sees it's still active."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        checkpoint_interval_seconds=60.0,
        mode="fish",
    )
    sub = FakeSubject(
        subject_id=0, label="fish", center=(960, 900),
        bbox=(900, 840, 1020, 960),
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    analyzer.analyze([sub], now_ts=0.0)
    # 61 seconds later → checkpoint should fire.
    events = analyzer.analyze([sub], now_ts=61.0)
    assert len(events) == 1
    assert events[0].behavior == Behavior.RESTING


def test_state_forgotten_when_subject_disappears():
    """If a subject vanishes (e.g. left the frame), its state is
    cleared so a returning detection with the same ID starts fresh."""
    analyzer = BehaviorAnalyzer(
        resting_speed_threshold=2.0,
        checkpoint_interval_seconds=60.0,
        mode="fish",
    )
    sub = FakeSubject(
        subject_id=0, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((500, 500), (0, 0), 30),
    )
    analyzer.analyze([sub], now_ts=0.0)
    # Tick with no subjects → state cleared.
    analyzer.analyze([], now_ts=10.0)
    # Subject returns with same ID at the same place → must emit (because
    # this is now treated as a brand new sighting).
    events = analyzer.analyze([sub], now_ts=20.0)
    assert len(events) == 1


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        BehaviorAnalyzer(mode="goldfish-but-with-extra-steps")
