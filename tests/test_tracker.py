"""Tests for src/inference/tracker.py"""

from inference.detector import Detection
from inference.tracker import CentroidTracker, TrackedFish


class TestTrackedFish:
    def test_total_distance_no_trajectory(self):
        fish = TrackedFish(fish_id=0, label="fish", center=(100, 100), bbox=(0, 0, 200, 200))
        assert fish.total_distance == 0.0

    def test_total_distance_single_point(self):
        fish = TrackedFish(
            fish_id=0, label="fish", center=(100, 100), bbox=(0, 0, 200, 200),
            trajectory=[(100, 100)],
        )
        assert fish.total_distance == 0.0

    def test_total_distance_multiple_points(self):
        fish = TrackedFish(
            fish_id=0, label="fish", center=(100, 100), bbox=(0, 0, 200, 200),
            trajectory=[(0, 0), (3, 4)],
        )
        assert fish.total_distance == 5.0

    def test_zone_surface(self):
        fish = TrackedFish(fish_id=0, label="fish", center=(500, 100), bbox=(0, 0, 100, 100))
        assert fish.zone == "surface"

    def test_zone_midwater(self):
        fish = TrackedFish(fish_id=0, label="fish", center=(500, 500), bbox=(0, 0, 100, 100))
        assert fish.zone == "midwater"

    def test_zone_bottom(self):
        fish = TrackedFish(fish_id=0, label="fish", center=(500, 800), bbox=(0, 0, 100, 100))
        assert fish.zone == "bottom"


class TestCentroidTracker:
    def _make_detection(self, x, y, label="fish"):
        return Detection(label=label, confidence=0.9, bbox=(x - 10, y - 10, x + 10, y + 10))

    def test_init(self):
        tracker = CentroidTracker()
        assert tracker.max_missing_frames == 30
        assert tracker.max_distance == 120.0
        assert tracker.active_fish == []

    def test_register_first_detections(self):
        tracker = CentroidTracker()
        dets = [self._make_detection(100, 100), self._make_detection(200, 200)]
        result = tracker.update(dets)
        assert len(result) == 2
        assert result[0].fish_id == 0
        assert result[1].fish_id == 1

    def test_empty_detections_increment_missing(self):
        tracker = CentroidTracker(max_missing_frames=2)
        tracker.update([self._make_detection(100, 100)])
        assert len(tracker.active_fish) == 1

        tracker.update([])
        assert tracker.active_fish[0].frames_missing == 1

        tracker.update([])
        assert tracker.active_fish[0].frames_missing == 2

        tracker.update([])
        assert len(tracker.active_fish) == 0

    def test_match_close_detection(self):
        tracker = CentroidTracker()
        tracker.update([self._make_detection(100, 100)])
        result = tracker.update([self._make_detection(105, 105)])
        assert len(result) == 1
        assert result[0].fish_id == 0
        assert result[0].frames_tracked == 1

    def test_register_new_when_far(self):
        tracker = CentroidTracker(max_distance=50.0)
        tracker.update([self._make_detection(100, 100)])
        result = tracker.update([self._make_detection(100, 100), self._make_detection(500, 500)])
        assert len(result) == 2

    def test_trajectory_capped(self):
        tracker = CentroidTracker(trajectory_length=3)
        tracker.update([self._make_detection(100, 100)])
        for i in range(5):
            tracker.update([self._make_detection(100 + i, 100)])
        fish = tracker.active_fish[0]
        assert len(fish.trajectory) <= 3

    def test_stale_tracks_removed(self):
        tracker = CentroidTracker(max_missing_frames=1)
        tracker.update([self._make_detection(100, 100)])
        # Introduce a far-away detection that won't match
        tracker.update([self._make_detection(900, 900)])
        # Old track at (100,100) should be removed after 1 missing frame
        # The far away one becomes a new track
        result = tracker.update([self._make_detection(900, 900)])
        ids = [f.fish_id for f in result]
        # Original fish_id=0 should be gone
        assert 0 not in ids

    def test_empty_update_on_empty_tracker(self):
        tracker = CentroidTracker()
        result = tracker.update([])
        assert result == []
