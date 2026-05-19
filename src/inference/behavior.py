"""
Classify subject behavior from tracking data.

Takes trajectories + detection metadata and produces human-readable
behavior labels used in the text summaries sent to Claude. Rules are
mode-conditional — "glass surfing" is fish-specific (named after fish
pacing along tank walls), "pacing" is the kennel-dog analogue (same
physics, recognized canine stress indicator), and so on.
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Behavior(str, Enum):
    RESTING = "resting"
    CRUISING = "cruising"
    DARTING = "darting"
    SURFACE_BREATHING = "surface_breathing"  # fish-only
    BOTTOM_DWELLING = "bottom_dwelling"
    GLASS_SURFING = "glass_surfing"  # fish-only
    PACING = "pacing"  # dog-only (kennel pacing — stress indicator)
    FEEDING = "feeding"
    HIDING = "hiding"
    SCHOOLING = "schooling"
    TERRITORIAL = "territorial"
    UNKNOWN = "unknown"


@dataclass
class BehaviorEvent:
    subject_id: int
    subject_label: str
    behavior: Behavior
    confidence: float
    zone: str
    duration_frames: int
    description: str


# Zone label vocabularies, indexed by mode. The classifier maps y-coordinate
# into one of these via vertical thirds of the frame.
_ZONE_VOCAB = {
    "fish": ("surface", "midwater", "bottom"),
    "dog": ("upper", "middle", "floor"),
}

# Free-text container noun per mode, used in human-readable descriptions.
_CONTAINER = {"fish": "tank", "dog": "kennel"}


class BehaviorAnalyzer:
    """Rule-based behavior classifier.

    Args:
        mode: ``"fish"`` or ``"dog"``. Selects the behavior vocabulary,
            zone labels, and description phrasing.
    """

    def __init__(
        self,
        darting_speed_threshold: float = 40.0,
        resting_speed_threshold: float = 2.0,
        glass_surf_edge_margin: int = 80,
        frame_width: int = 1920,
        frame_height: int = 1080,
        min_behavior_frames: int = 10,
        mode: str = "fish",
    ):
        if mode not in _ZONE_VOCAB:
            raise ValueError(
                f"Unknown mode {mode!r}. Must be one of {list(_ZONE_VOCAB)}."
            )
        self.mode = mode
        self.darting_speed = darting_speed_threshold
        self.resting_speed = resting_speed_threshold
        self.edge_margin = glass_surf_edge_margin
        self.frame_w = frame_width
        self.frame_h = frame_height
        self.min_frames = min_behavior_frames

    # --- public ---------------------------------------------------------

    def zone_for(self, center: Tuple[int, int]) -> str:
        """Return the zone label for a given center point under the
        current mode."""
        _, y = center
        upper, mid, lower = _ZONE_VOCAB[self.mode]
        if y < self.frame_h / 3:
            return upper
        if y < self.frame_h * 2 / 3:
            return mid
        return lower

    def analyze(self, tracked_subjects: list) -> List[BehaviorEvent]:
        events: List[BehaviorEvent] = []
        for sub in tracked_subjects:
            if sub.frames_tracked < self.min_frames:
                continue
            zone = self.zone_for(sub.center)
            behavior, confidence, description = self._classify(sub, zone)
            events.append(
                BehaviorEvent(
                    subject_id=sub.subject_id,
                    subject_label=sub.label,
                    behavior=behavior,
                    confidence=confidence,
                    zone=zone,
                    duration_frames=sub.frames_tracked,
                    description=description,
                )
            )
        return events

    # --- internal -------------------------------------------------------

    def _classify(self, sub, zone: str) -> Tuple[Behavior, float, str]:
        traj = sub.trajectory
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
        container = _CONTAINER[self.mode]

        # 1. Darting — sudden bursts. Same logic both modes.
        if max_speed > self.darting_speed:
            verb = "dart" if self.mode == "fish" else "run"
            return (
                Behavior.DARTING,
                min(max_speed / (self.darting_speed * 2), 1.0),
                f"{sub.label} made a sudden {verb} across the {container} "
                f"(peak speed: {max_speed:.0f}px/frame)",
            )

        # 2. Wall pacing — fish call it glass-surfing, dogs call it pacing.
        edge_count = sum(
            1 for x, _ in recent
            if x < self.edge_margin or x > self.frame_w - self.edge_margin
        )
        if edge_count > len(recent) * 0.6:
            if self.mode == "fish":
                return (
                    Behavior.GLASS_SURFING,
                    edge_count / len(recent),
                    f"{sub.label} is glass surfing — swimming back and "
                    f"forth along the tank wall",
                )
            return (
                Behavior.PACING,
                edge_count / len(recent),
                f"{sub.label} is pacing back and forth along the side "
                f"of the kennel (a recognized stress indicator)",
            )

        # 3. Surface-breathing — fish only. Surface zone + slow.
        if self.mode == "fish":
            upper_zone = _ZONE_VOCAB["fish"][0]  # "surface"
            if zone == upper_zone and avg_speed < self.resting_speed * 3:
                return (
                    Behavior.SURFACE_BREATHING,
                    0.7,
                    f"{sub.label} is hanging near the surface, possibly "
                    f"gulping air",
                )

        # 4. Resting — low speed anywhere.
        if avg_speed < self.resting_speed:
            verb = "resting" if self.mode == "fish" else "lying still"
            return (
                Behavior.RESTING,
                1.0 - (avg_speed / self.resting_speed) if self.resting_speed else 1.0,
                f"{sub.label} is {verb} near the {zone} of the {container}",
            )

        # 5. Default — cruising / wandering.
        verb = "cruising" if self.mode == "fish" else "wandering"
        return (
            Behavior.CRUISING,
            0.8,
            f"{sub.label} is {verb} through the {zone} of the {container} "
            f"at a relaxed pace",
        )
