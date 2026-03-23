"""Tests for src/inference/behavior.py"""

from inference.behavior import Behavior, BehaviorAnalyzer, BehaviorEvent
from inference.tracker import TrackedFish


class TestBehavior:
    def test_enum_values(self):
        assert Behavior.RESTING == "resting"
        assert Behavior.CRUISING == "cruising"
        assert Behavior.DARTING == "darting"
        assert Behavior.GLASS_SURFING == "glass_surfing"
        assert Behavior.SURFACE_BREATHING == "surface_breathing"
        assert Behavior.UNKNOWN == "unknown"


class TestBehaviorEvent:
    def test_fields(self):
        event = BehaviorEvent(
            fish_id=0, fish_label="fish", behavior=Behavior.CRUISING,
            confidence=0.8, zone="midwater", duration_frames=50,
            description="Fish is cruising",
        )
        assert event.fish_id == 0
        assert event.behavior == Behavior.CRUISING


class TestBehaviorAnalyzer:
    def _make_fish(self, trajectory, label="fish", frames_tracked=20):
        fish = TrackedFish(
            fish_id=0, label=label, center=trajectory[-1] if trajectory else (0, 0),
            bbox=(0, 0, 100, 100), frames_tracked=frames_tracked,
            trajectory=trajectory,
        )
        return fish

    def test_skip_insufficient_frames(self):
        analyzer = BehaviorAnalyzer(min_behavior_frames=10)
        fish = self._make_fish([(100, 100)], frames_tracked=5)
        events = analyzer.analyze([fish])
        assert events == []

    def test_unknown_short_trajectory(self):
        analyzer = BehaviorAnalyzer()
        fish = self._make_fish([(100, 100)], frames_tracked=20)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.UNKNOWN

    def test_resting(self):
        analyzer = BehaviorAnalyzer(resting_speed_threshold=5.0)
        # Fish barely moving
        traj = [(500, 500 + i * 0.1) for i in range(30)]
        fish = self._make_fish(traj, frames_tracked=30)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.RESTING

    def test_darting(self):
        analyzer = BehaviorAnalyzer(darting_speed_threshold=10.0)
        # Fish making a big jump
        traj = [(100, 100)] * 20 + [(100, 100), (200, 200)]
        fish = self._make_fish(traj, frames_tracked=22)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.DARTING

    def test_cruising(self):
        analyzer = BehaviorAnalyzer(
            resting_speed_threshold=1.0, darting_speed_threshold=100.0,
        )
        # Moderate, steady movement in midwater
        traj = [(500 + i * 5, 500) for i in range(30)]
        fish = self._make_fish(traj, frames_tracked=30)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.CRUISING

    def test_glass_surfing(self):
        analyzer = BehaviorAnalyzer(
            glass_surf_edge_margin=100, frame_width=1920,
            darting_speed_threshold=200.0,
        )
        # Fish near the left edge (x < 100)
        traj = [(50 + i % 30, 500) for i in range(30)]
        fish = self._make_fish(traj, frames_tracked=30)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.GLASS_SURFING

    def test_surface_breathing(self):
        analyzer = BehaviorAnalyzer(
            resting_speed_threshold=5.0, darting_speed_threshold=200.0,
            glass_surf_edge_margin=10,
        )
        # Fish at the surface (y < 360) with slow speed
        traj = [(500, 100 + i * 0.5) for i in range(30)]
        fish = self._make_fish(traj, frames_tracked=30)
        events = analyzer.analyze([fish])
        assert events[0].behavior == Behavior.SURFACE_BREATHING
