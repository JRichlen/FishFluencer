"""
Multi-object centroid tracker for persistent subject identity across frames.

Assigns stable IDs to detected subjects (fish or dogs) so we can track
individual movement patterns over time. Upgrade path: swap for DeepSORT
if you need re-identification after occlusion.
"""

import logging
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Tuple

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
    def __init__(
        self,
        max_missing_frames: int = 30,
        max_distance: float = 120.0,
        trajectory_length: int = 300,
    ):
        self.max_missing_frames = max_missing_frames
        self.max_distance = max_distance
        self.trajectory_length = trajectory_length

        self._next_id = 0
        self._tracked: "OrderedDict[int, TrackedSubject]" = OrderedDict()

    @property
    def active_subjects(self) -> List[TrackedSubject]:
        return list(self._tracked.values())

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
        sub = TrackedSubject(
            subject_id=self._next_id,
            label=detection.label,
            center=detection.center,
            bbox=detection.bbox,
            trajectory=[detection.center],
        )
        self._tracked[self._next_id] = sub
        logger.debug(
            "New subject registered: #%d (%s)", self._next_id, detection.label
        )
        self._next_id += 1
