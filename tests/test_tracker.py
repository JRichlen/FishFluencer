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


def test_register_new_subject():
    tracker = CentroidTracker()
    subs = tracker.update([det("fish", 100, 100)])
    assert len(subs) == 1
    assert subs[0].subject_id == 0
    assert subs[0].label == "fish"


def test_register_works_for_dog_label():
    tracker = CentroidTracker()
    subs = tracker.update([det("dog", 500, 500)])
    assert subs[0].label == "dog"


def test_track_movement_preserves_id():
    tracker = CentroidTracker(max_distance=200.0)
    tracker.update([det("fish", 100, 100)])
    tracker.update([det("fish", 120, 110)])
    tracked = tracker.update([det("fish", 140, 120)])
    assert len(tracked) == 1
    assert tracked[0].subject_id == 0
    assert tracked[0].frames_tracked == 2


def test_deregister_after_missing():
    tracker = CentroidTracker(max_missing_frames=2)
    tracker.update([det("fish", 100, 100)])
    tracker.update([])
    tracker.update([])
    tracker.update([])
    assert tracker.active_subjects == []


def test_separate_subjects_get_separate_ids():
    tracker = CentroidTracker(max_distance=80.0)
    tracker.update([det("fish", 100, 100), det("fish", 800, 100)])
    assert len({s.subject_id for s in tracker.active_subjects}) == 2
