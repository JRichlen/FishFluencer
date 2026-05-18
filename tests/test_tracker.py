"""Centroid tracker tests — verify identity is preserved across frames."""

from dataclasses import dataclass

from src.inference.tracker import CentroidTracker


@dataclass
class FakeDetection:
    label: str
    confidence: float
    bbox: tuple
    center: tuple


def det(label, cx, cy):
    half = 30
    return FakeDetection(
        label=label,
        confidence=0.9,
        bbox=(cx - half, cy - half, cx + half, cy + half),
        center=(cx, cy),
    )


def test_register_new_fish():
    tracker = CentroidTracker()
    fish = tracker.update([det("fish", 100, 100)])
    assert len(fish) == 1
    assert fish[0].fish_id == 0
    assert fish[0].label == "fish"


def test_track_movement_preserves_id():
    tracker = CentroidTracker(max_distance=200.0)
    tracker.update([det("fish", 100, 100)])
    tracker.update([det("fish", 120, 110)])
    tracked = tracker.update([det("fish", 140, 120)])
    assert len(tracked) == 1
    assert tracked[0].fish_id == 0
    assert tracked[0].frames_tracked == 2


def test_deregister_after_missing():
    tracker = CentroidTracker(max_missing_frames=2)
    tracker.update([det("fish", 100, 100)])
    tracker.update([])
    tracker.update([])
    tracker.update([])
    assert tracker.active_fish == []


def test_separate_fish_get_separate_ids():
    tracker = CentroidTracker(max_distance=80.0)
    tracker.update([det("fish", 100, 100), det("fish", 800, 100)])
    assert len({f.fish_id for f in tracker.active_fish}) == 2
