"""
Multi-object centroid tracker with persistent subject identity.

Assigns stable IDs to detected subjects (fish or dogs) so we can track
individual movement patterns over time. Upgrade path: swap for DeepSORT
if you need appearance-based re-identification after occlusion.

Tier 2: identity now persists across program restarts via a JSON
state file. On startup, the tracker loads `next_id` and the
last-seen (center, label) of recently-tracked subjects. When a new
detection appears within `rehydrate_radius` of a saved subject's last
position AND its label matches, the saved ID is reused instead of
allocating a fresh one. This is poor-man's re-ID — it works well for
the "kennel resident lives in roughly the same spot" case, fails for
roaming subjects, and that's acceptable for Tier 2.
"""

import json
import logging
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TrackedSubject:
    subject_id: int
    label: str
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    frames_tracked: int = 0
    frames_missing: int = 0
    trajectory: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def total_distance(self) -> float:
        if len(self.trajectory) < 2:
            return 0.0
        dist = 0.0
        for i in range(1, len(self.trajectory)):
            x1, y1 = self.trajectory[i - 1]
            x2, y2 = self.trajectory[i]
            dist += math.hypot(x2 - x1, y2 - y1)
        return dist


class CentroidTracker:
    """Multi-object centroid tracker.

    Args:
        max_missing_frames: drop a track after this many consecutive
            frames without a matching detection.
        max_distance: in-session distance threshold (pixels) for
            matching a detection to an existing track.
        trajectory_length: cap on stored trajectory points per subject.
        state_path: optional path to a JSON file used to persist
            ``next_id`` and the last-seen position/label of recently
            tracked subjects across restarts. ``None`` disables
            persistence.
        rehydrate_radius: on startup, a new detection within this
            many pixels of a previously-saved subject's last position
            with the same label reuses the saved ID. Defaults to 2x
            ``max_distance`` because saved positions are typically
            seconds-to-minutes old (a full restart cycle).
        rehydrate_ttl_seconds: ignore saved subjects older than this
            (default 24 h). Prevents stale state from a week-old crash
            silently re-assigning IDs.
    """

    def __init__(
        self,
        max_missing_frames: int = 30,
        max_distance: float = 120.0,
        trajectory_length: int = 300,
        state_path: Optional[str] = None,
        rehydrate_radius: Optional[float] = None,
        rehydrate_ttl_seconds: float = 86400.0,
    ):
        self.max_missing_frames = max_missing_frames
        self.max_distance = max_distance
        self.trajectory_length = trajectory_length
        self.state_path = Path(state_path) if state_path else None
        self.rehydrate_radius = (
            rehydrate_radius if rehydrate_radius is not None else max_distance * 2
        )
        self.rehydrate_ttl_seconds = rehydrate_ttl_seconds

        self._next_id = 0
        self._tracked: "OrderedDict[int, TrackedSubject]" = OrderedDict()

        # Saved subjects (loaded from state_path on construction).
        # Format: { subject_id: {"label": str, "center": (x, y), "saved_at": float } }
        self._saved_subjects: Dict[int, dict] = {}
        if self.state_path:
            self._load_state()

    @property
    def active_subjects(self) -> List[TrackedSubject]:
        return list(self._tracked.values())

    @property
    def next_id(self) -> int:
        return self._next_id

    def update(self, detections: list) -> List[TrackedSubject]:
        if not detections:
            to_remove = []
            for sid, sub in self._tracked.items():
                sub.frames_missing += 1
                if sub.frames_missing > self.max_missing_frames:
                    to_remove.append(sid)
            for sid in to_remove:
                logger.debug("Subject #%d deregistered (missing too long)", sid)
                del self._tracked[sid]
            return self.active_subjects

        det_centers = [d.center for d in detections]

        if not self._tracked:
            for det in detections:
                self._register(det)
            return self.active_subjects

        track_ids = list(self._tracked.keys())
        track_centers = [self._tracked[tid].center for tid in track_ids]

        distances = []
        for tc in track_centers:
            row = [math.hypot(tc[0] - dc[0], tc[1] - dc[1]) for dc in det_centers]
            distances.append(row)

        matched_tracks: set = set()
        matched_dets: set = set()

        pairs = []
        for ti in range(len(track_ids)):
            for di in range(len(detections)):
                pairs.append((distances[ti][di], ti, di))
        pairs.sort()

        for dist, ti, di in pairs:
            if ti in matched_tracks or di in matched_dets:
                continue
            if dist > self.max_distance:
                continue
            sub = self._tracked[track_ids[ti]]
            sub.center = detections[di].center
            sub.bbox = detections[di].bbox
            sub.label = detections[di].label
            sub.frames_tracked += 1
            sub.frames_missing = 0
            sub.trajectory.append(sub.center)
            if len(sub.trajectory) > self.trajectory_length:
                sub.trajectory.pop(0)

            matched_tracks.add(ti)
            matched_dets.add(di)

        for ti in range(len(track_ids)):
            if ti not in matched_tracks:
                self._tracked[track_ids[ti]].frames_missing += 1

        to_remove = [
            tid for tid, sub in self._tracked.items()
            if sub.frames_missing > self.max_missing_frames
        ]
        for tid in to_remove:
            del self._tracked[tid]

        for di in range(len(detections)):
            if di not in matched_dets:
                self._register(detections[di])

        return self.active_subjects

    def _register(self, detection) -> None:
        """Allocate an ID for an unmatched detection. Prefers reusing a
        previously-saved ID when the detection's position + label match
        a saved subject within ``rehydrate_radius``."""
        reused_id = self._take_saved_id(detection)
        sid = reused_id if reused_id is not None else self._next_id
        if reused_id is None:
            self._next_id += 1

        sub = TrackedSubject(
            subject_id=sid,
            label=detection.label,
            center=detection.center,
            bbox=detection.bbox,
            trajectory=[detection.center],
        )
        self._tracked[sid] = sub
        logger.debug(
            "Subject registered: #%d (%s)%s",
            sid,
            detection.label,
            " [rehydrated from saved state]" if reused_id is not None else "",
        )

    def _take_saved_id(self, detection) -> Optional[int]:
        """If a saved subject matches this detection by label + nearby
        center, return its ID (and remove it from the saved pool so it
        can't be reused for another detection in the same tick)."""
        if not self._saved_subjects:
            return None
        best_id = None
        best_dist = float("inf")
        dx_target, dy_target = detection.center
        for sid, info in self._saved_subjects.items():
            if info["label"] != detection.label:
                continue
            sx, sy = info["center"]
            dist = math.hypot(sx - dx_target, sy - dy_target)
            if dist <= self.rehydrate_radius and dist < best_dist:
                best_dist = dist
                best_id = sid
        if best_id is not None:
            del self._saved_subjects[best_id]
        return best_id

    # --- persistence ----------------------------------------------------

    def save_state(self) -> None:
        """Write current tracker state to ``state_path`` (if configured)."""
        if not self.state_path:
            return
        now = time.time()
        subjects = {}
        # Include subjects still actively tracked.
        for sid, sub in self._tracked.items():
            subjects[str(sid)] = {
                "label": sub.label,
                "center": list(sub.center),
                "saved_at": now,
            }
        # Carry forward saved-but-not-yet-rehydrated subjects, in case
        # the service restarts again before any of them are matched.
        for sid, info in self._saved_subjects.items():
            subjects.setdefault(str(sid), info)

        state = {
            "next_id": self._next_id,
            "subjects": subjects,
        }
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(state))
            tmp.replace(self.state_path)
            logger.debug(
                "Tracker state saved (%d subjects, next_id=%d)",
                len(subjects), self._next_id,
            )
        except Exception as e:  # filesystem failure shouldn't crash the agent
            logger.warning("Failed to save tracker state: %s", e)

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            state = json.loads(self.state_path.read_text())
        except Exception as e:
            logger.warning("Tracker state file unreadable (%s) — starting fresh", e)
            return

        self._next_id = int(state.get("next_id", 0))
        cutoff = time.time() - self.rehydrate_ttl_seconds
        raw = state.get("subjects", {})
        kept = 0
        for sid_str, info in raw.items():
            saved_at = info.get("saved_at", 0)
            if saved_at < cutoff:
                continue
            self._saved_subjects[int(sid_str)] = {
                "label": info["label"],
                "center": tuple(info["center"]),
                "saved_at": saved_at,
            }
            kept += 1
        logger.info(
            "Tracker rehydrated: next_id=%d, %d/%d saved subjects within TTL",
            self._next_id, kept, len(raw),
        )
