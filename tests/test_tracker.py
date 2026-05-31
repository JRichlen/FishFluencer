"""Centroid tracker tests — identity persistence within and across runs."""

import json
import time
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


# --- Tier 2: identity persistence across restarts ----------------------


def test_state_file_round_trip(tmp_path):
    """Saving and reloading state should restore next_id and saved
    subjects for ID reuse."""
    state_path = tmp_path / "tracker_state.json"

    t1 = CentroidTracker(state_path=str(state_path))
    t1.update([det("dog", 500, 500)])
    t1.update([det("dog", 510, 505)])
    t1.update([det("dog", 520, 510)])
    saved_id = t1.active_subjects[0].subject_id
    t1.save_state()

    # Verify the file actually contains the subject.
    state = json.loads(state_path.read_text())
    assert "subjects" in state
    assert state["next_id"] >= 1

    # Restart: new tracker reads the file.
    t2 = CentroidTracker(state_path=str(state_path))
    assert t2.next_id == t1.next_id

    # New detection at roughly the same position → ID gets reused.
    subs = t2.update([det("dog", 525, 515)])
    assert subs[0].subject_id == saved_id


def test_rehydration_requires_matching_label(tmp_path):
    """A saved `dog` shouldn't lend its ID to a fresh `cat` detection
    at the same place — different labels = different subjects."""
    state_path = tmp_path / "tracker_state.json"

    t1 = CentroidTracker(state_path=str(state_path))
    t1.update([det("dog", 500, 500)])
    t1.update([det("dog", 510, 505)])
    t1.save_state()

    t2 = CentroidTracker(state_path=str(state_path))
    subs = t2.update([det("cat", 500, 500)])
    # New ID — the saved dog ID is NOT reused for a cat.
    assert subs[0].subject_id != 0
    # next_id from the saved state, so this cat gets the NEXT id.
    assert subs[0].subject_id == t1.next_id


def test_rehydration_radius_limits_position_match(tmp_path):
    """A detection far from the saved position should NOT reuse the
    saved ID, even with the same label."""
    state_path = tmp_path / "tracker_state.json"

    t1 = CentroidTracker(state_path=str(state_path), max_distance=120.0)
    # rehydrate_radius defaults to 2 × max_distance = 240
    t1.update([det("dog", 100, 100)])
    t1.update([det("dog", 105, 105)])
    t1.save_state()

    t2 = CentroidTracker(state_path=str(state_path), max_distance=120.0)
    # Detection 500px away — well outside the rehydrate radius.
    subs = t2.update([det("dog", 700, 700)])
    assert subs[0].subject_id != 0


def test_stale_saved_state_dropped(tmp_path):
    """Saved subjects older than the TTL should be ignored on load."""
    state_path = tmp_path / "tracker_state.json"
    state_path.write_text(json.dumps({
        "next_id": 5,
        "subjects": {
            "0": {"label": "dog", "center": [100, 100],
                  "saved_at": time.time() - 999999},  # very old
        },
    }))

    t = CentroidTracker(state_path=str(state_path), rehydrate_ttl_seconds=60)
    # next_id is preserved (so we don't collide with old IDs)
    assert t.next_id == 5
    # New detection at the saved position should get a fresh ID,
    # not subject_id=0 (which was the stale saved one).
    subs = t.update([det("dog", 100, 100)])
    assert subs[0].subject_id == 5


def test_state_path_none_disables_persistence(tmp_path):
    """state_path=None means no save and no load (no file written)."""
    t = CentroidTracker(state_path=None)
    t.update([det("dog", 100, 100)])
    t.save_state()  # no-op
    # No files anywhere should mention tracker.
    assert not list(tmp_path.glob("*tracker*"))


def test_missing_state_file_starts_fresh(tmp_path):
    """If state_path points at a file that doesn't exist, just start
    with next_id=0 and no saved subjects."""
    state_path = tmp_path / "nope.json"
    t = CentroidTracker(state_path=str(state_path))
    assert t.next_id == 0


def test_corrupt_state_file_starts_fresh(tmp_path):
    """Garbage in the state file should NOT crash the tracker."""
    state_path = tmp_path / "bad.json"
    state_path.write_text("not valid json {{{")
    t = CentroidTracker(state_path=str(state_path))
    assert t.next_id == 0
