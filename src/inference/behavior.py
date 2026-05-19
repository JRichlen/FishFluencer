"""
Classify subject behavior from tracking data.

Takes trajectories + bounding boxes and produces human-readable
behavior labels used in the text summaries sent to Claude. Rules are
mode-conditional — fish-mode and dog-mode share most logic but use
different vocabularies and trigger different rules.

Tier 2 additions:
  - Posture detection for dog mode (LYING_DOWN / SITTING / STANDING)
    derived from bbox aspect ratio. This requires a side-angle camera
    mount (see `docs/hardware/dog-kennel-mounting.md`); top-down
    mounts produce a roughly square bbox regardless of posture and
    will degrade to undifferentiated RESTING.
  - Span-based event emission: the analyzer holds per-subject state
    and only emits when a subject's classification changes, plus a
    periodic checkpoint every `checkpoint_interval_seconds` so an
    ongoing behavior shows up in the summary window before it ends.
    Drops DB volume from one row per frame to ~one row per minute
    per subject.
"""

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Behavior(str, Enum):
    RESTING = "resting"
    CRUISING = "cruising"
    DARTING = "darting"
    SURFACE_BREATHING = "surface_breathing"  # fish-only
    BOTTOM_DWELLING = "bottom_dwelling"
    GLASS_SURFING = "glass_surfing"  # fish-only
    PACING = "pacing"  # dog-only (kennel pacing — stress indicator)
    LYING_DOWN = "lying_down"  # dog-only posture
    SITTING = "sitting"  # dog-only posture
    STANDING = "standing"  # dog-only posture
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


def _bbox_aspect(bbox: Tuple[int, int, int, int]) -> float:
    """Return bbox width / height. Larger values = wider than tall
    (typical of a lying-down dog seen from the side)."""
    xmin, ymin, xmax, ymax = bbox
    height = max(1, ymax - ymin)
    width = max(0, xmax - xmin)
    return width / height


class BehaviorAnalyzer:
    """Rule-based behavior classifier with per-subject state.

    Args:
        mode: ``"fish"`` or ``"dog"``. Selects vocabulary, zone labels,
            and which posture/behavior rules fire.
        checkpoint_interval_seconds: how often to re-emit a sustained
            behavior so it surfaces in the next summary window. Default
            60s. Set higher to reduce DB writes for very stable subjects.
        posture_aspect_lying: bbox width/height ratio above which a
            still dog is classified as ``LYING_DOWN``. Default 1.4
            (calibrated for a side-mounted camera).
        posture_aspect_sitting: bbox aspect below which a still dog is
            classified as ``STANDING`` (taller than wide). Default 0.9.
            Between this and ``posture_aspect_lying`` the dog is
            classified as ``SITTING``.
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
        checkpoint_interval_seconds: float = 60.0,
        posture_aspect_lying: float = 1.4,
        posture_aspect_sitting: float = 0.9,
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
        self.checkpoint_interval = checkpoint_interval_seconds
        self.posture_aspect_lying = posture_aspect_lying
        self.posture_aspect_sitting = posture_aspect_sitting

        # Per-subject state — drives transition + checkpoint logic.
        self._last_behavior: Dict[int, Behavior] = {}
        self._last_emit_ts: Dict[int, float] = {}

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

    def analyze(
        self,
        tracked_subjects: list,
        now_ts: Optional[float] = None,
    ) -> List[BehaviorEvent]:
        """Run classification over the current tracker output.

        Emits one event per subject only when:
          - the subject is newly tracked above ``min_behavior_frames``
          - its classification has changed since the last frame, OR
          - ``checkpoint_interval_seconds`` has elapsed since the last
            emission for that subject.

        Subjects that were tracked previously but disappeared from the
        input list have their span state forgotten.
        """
        ts = now_ts if now_ts is not None else time.time()
        events: List[BehaviorEvent] = []
        seen_ids = set()

        for sub in tracked_subjects:
            seen_ids.add(sub.subject_id)
            if sub.frames_tracked < self.min_frames:
                continue

            zone = self.zone_for(sub.center)
            new_behavior, confidence, description = self._classify(sub, zone)

            last_b = self._last_behavior.get(sub.subject_id)
            last_emit = self._last_emit_ts.get(sub.subject_id, 0.0)

            should_emit = (
                last_b is None
                or last_b != new_behavior
                or (ts - last_emit) >= self.checkpoint_interval
            )
            if not should_emit:
                continue

            events.append(
                BehaviorEvent(
                    subject_id=sub.subject_id,
                    subject_label=sub.label,
                    behavior=new_behavior,
                    confidence=confidence,
                    zone=zone,
                    duration_frames=sub.frames_tracked,
                    description=description,
                )
            )
            self._last_behavior[sub.subject_id] = new_behavior
            self._last_emit_ts[sub.subject_id] = ts

        # Forget state for subjects that disappeared this tick.
        for sid in list(self._last_behavior):
            if sid not in seen_ids:
                del self._last_behavior[sid]
                self._last_emit_ts.pop(sid, None)

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

        # 1. Darting / running — sudden bursts. Both modes.
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

        # 3. Surface-breathing — fish only.
        if self.mode == "fish":
            upper_zone = _ZONE_VOCAB["fish"][0]  # "surface"
            if zone == upper_zone and avg_speed < self.resting_speed * 3:
                return (
                    Behavior.SURFACE_BREATHING,
                    0.7,
                    f"{sub.label} is hanging near the surface, possibly "
                    f"gulping air",
                )

        # 4. Posture-aware resting — dog only.
        #    A still dog gets a posture-specific classification based
        #    on bbox aspect ratio. Camera mount matters here — a top-
        #    down view produces a square-ish bbox regardless of pose
        #    and degrades to undifferentiated SITTING.
        if self.mode == "dog" and avg_speed < self.resting_speed:
            aspect = _bbox_aspect(sub.bbox)
            if aspect >= self.posture_aspect_lying:
                return (
                    Behavior.LYING_DOWN,
                    min(aspect / (self.posture_aspect_lying * 1.5), 1.0),
                    f"{sub.label} is lying down in the {zone} of the "
                    f"{container} (bbox aspect {aspect:.2f})",
                )
            if aspect <= self.posture_aspect_sitting:
                return (
                    Behavior.STANDING,
                    0.65,
                    f"{sub.label} is standing still in the {zone} of "
                    f"the {container} (bbox aspect {aspect:.2f})",
                )
            return (
                Behavior.SITTING,
                0.7,
                f"{sub.label} is sitting in the {zone} of the "
                f"{container} (bbox aspect {aspect:.2f})",
            )

        # 5. Resting — fish-mode catch-all.
        if avg_speed < self.resting_speed:
            return (
                Behavior.RESTING,
                1.0 - (avg_speed / self.resting_speed) if self.resting_speed else 1.0,
                f"{sub.label} is resting near the {zone} of the {container}",
            )

        # 6. Default — cruising / wandering.
        verb = "cruising" if self.mode == "fish" else "wandering"
        return (
            Behavior.CRUISING,
            0.8,
            f"{sub.label} is {verb} through the {zone} of the {container} "
            f"at a relaxed pace",
        )
