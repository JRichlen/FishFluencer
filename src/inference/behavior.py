"""
Classify fish behavior from tracking data.

Takes trajectories + detection metadata and produces human-readable
behavior labels used in the text summaries sent to Claude.
"""

import math
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)


class Behavior(str, Enum):
    RESTING = "resting"
    CRUISING = "cruising"
    DARTING = "darting"
    SURFACE_BREATHING = "surface_breathing"
    BOTTOM_DWELLING = "bottom_dwelling"
    GLASS_SURFING = "glass_surfing"
    FEEDING = "feeding"
    HIDING = "hiding"
    SCHOOLING = "schooling"
    TERRITORIAL = "territorial"
    UNKNOWN = "unknown"


@dataclass
class BehaviorEvent:
    fish_id: int
    fish_label: str
    behavior: Behavior
    confidence: float
    zone: str
    duration_frames: int
    description: str


class BehaviorAnalyzer:
    """Rule-based behavior classifier."""

    def __init__(
        self,
        darting_speed_threshold: float = 40.0,
        resting_speed_threshold: float = 2.0,
        glass_surf_edge_margin: int = 80,
        frame_width: int = 1920,
        frame_height: int = 1080,
        min_behavior_frames: int = 10,
    ):
        self.darting_speed = darting_speed_threshold
        self.resting_speed = resting_speed_threshold
        self.edge_margin = glass_surf_edge_margin
        self.frame_w = frame_width
        self.frame_h = frame_height
        self.min_frames = min_behavior_frames

    def analyze(self, tracked_fish: list) -> List[BehaviorEvent]:
        """Classify behavior for each tracked fish."""
        events: List[BehaviorEvent] = []

        for fish in tracked_fish:
            if fish.frames_tracked < self.min_frames:
                continue

            behavior, confidence, description = self._classify(fish)
            events.append(
                BehaviorEvent(
                    fish_id=fish.fish_id,
                    fish_label=fish.label,
                    behavior=behavior,
                    confidence=confidence,
                    zone=fish.zone,
                    duration_frames=fish.frames_tracked,
                    description=description,
                )
            )

        return events

    def _classify(self, fish) -> tuple:
        traj = fish.trajectory
        if len(traj) < 2:
            return Behavior.UNKNOWN, 0.0, "Not enough data"

        window = min(30, len(traj))
        recent = traj[-window:]
        speeds = []
        for i in range(1, len(recent)):
            dx = recent[i][0] - recent[i - 1][0]
            dy = recent[i][1] - recent[i - 1][1]
            speeds.append(math.hypot(dx, dy))

        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0

        if max_speed > self.darting_speed:
            return (
                Behavior.DARTING,
                min(max_speed / (self.darting_speed * 2), 1.0),
                f"{fish.label} made a sudden dart across the tank "
                f"(peak speed: {max_speed:.0f}px/frame)",
            )

        edge_count = sum(
            1
            for x, _y in recent
            if x < self.edge_margin or x > self.frame_w - self.edge_margin
        )
        if edge_count > len(recent) * 0.6:
            return (
                Behavior.GLASS_SURFING,
                edge_count / len(recent),
                f"{fish.label} is glass surfing — swimming back and forth "
                f"along the tank wall",
            )

        if fish.zone == "surface" and avg_speed < self.resting_speed * 3:
            return (
                Behavior.SURFACE_BREATHING,
                0.7,
                f"{fish.label} is hanging near the surface, possibly gulping air",
            )

        if avg_speed < self.resting_speed:
            return (
                Behavior.RESTING,
                1.0 - (avg_speed / self.resting_speed),
                f"{fish.label} is resting near the {fish.zone} of the tank",
            )

        return (
            Behavior.CRUISING,
            0.8,
            f"{fish.label} is cruising through the {fish.zone} at a relaxed pace",
        )
