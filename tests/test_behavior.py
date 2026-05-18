"""Behavior analyzer — classify based on trajectory shape."""

from dataclasses import dataclass, field
from typing import List, Tuple

from src.inference.behavior import Behavior, BehaviorAnalyzer


@dataclass
class FakeFish:
    fish_id: int
    label: str
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    frames_tracked: int = 30
    frames_missing: int = 0

    @property
    def zone(self) -> str:
        _, y = self.center
        if y < 360:
            return "surface"
        if y < 720:
            return "midwater"
        return "bottom"


def linear_trajectory(start, step, count):
    x, y = start
    dx, dy = step
    return [(x + dx * i, y + dy * i) for i in range(count)]


def test_resting():
    analyzer = BehaviorAnalyzer(resting_speed_threshold=2.0)
    fish = FakeFish(
        fish_id=0, label="fish", center=(960, 900),
        bbox=(900, 840, 1020, 960),
        trajectory=linear_trajectory((960, 900), (0, 0), 30),
    )
    events = analyzer.analyze([fish])
    assert events[0].behavior == Behavior.RESTING


def test_darting():
    analyzer = BehaviorAnalyzer(darting_speed_threshold=40.0)
    fish = FakeFish(
        fish_id=1, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=linear_trajectory((100, 500), (60, 0), 30),
    )
    events = analyzer.analyze([fish])
    assert events[0].behavior == Behavior.DARTING


def test_glass_surfing():
    analyzer = BehaviorAnalyzer(glass_surf_edge_margin=80, frame_width=1920)
    # All points within 80px of the left edge
    traj = [(40, 500 + i) for i in range(30)]
    fish = FakeFish(
        fish_id=2, label="fish", center=traj[-1],
        bbox=(20, traj[-1][1] - 20, 60, traj[-1][1] + 20),
        trajectory=traj,
    )
    events = analyzer.analyze([fish])
    assert events[0].behavior == Behavior.GLASS_SURFING


def test_skip_short_tracks():
    analyzer = BehaviorAnalyzer(min_behavior_frames=10)
    fish = FakeFish(
        fish_id=3, label="fish", center=(500, 500),
        bbox=(450, 450, 550, 550),
        trajectory=[(500, 500)],
        frames_tracked=5,
    )
    assert analyzer.analyze([fish]) == []
