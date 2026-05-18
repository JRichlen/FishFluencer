"""
Local image lifecycle management.

PRIVACY GUARANTEES:
  1. Images are stored ONLY in a local directory on the microSD card.
  2. Images are NEVER transmitted over any network interface.
  3. Images are auto-deleted after the configured retention period.
  4. Only text descriptions derived from images leave the device.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageManager:
    def __init__(
        self,
        storage_dir: str = "data/snapshots",
        retention_hours: float = 24.0,
        max_storage_mb: float = 500.0,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.retention_hours = retention_hours
        self.max_storage_bytes = max_storage_mb * 1024 * 1024

    def describe_frame(self, frame, detections: list) -> str:
        """Build a text description of a frame from its detections.

        This is what replaces sending the actual image over the network.
        """
        if not detections:
            return "Empty tank view — no fish visible in frame."

        parts = []
        for d in detections:
            x_pct = d.center[0] / 1920 * 100
            y_pct = d.center[1] / 1080 * 100
            position = self._describe_position(x_pct, y_pct)
            parts.append(
                f"A {d.label} (confidence {d.confidence:.0%}) "
                f"detected at the {position} of the tank"
            )

        return ". ".join(parts) + "."

    def _describe_position(self, x_pct: float, y_pct: float) -> str:
        v = "top" if y_pct < 33 else "middle" if y_pct < 66 else "bottom"
        h = "left" if x_pct < 33 else "center" if x_pct < 66 else "right"
        return f"{v}-{h}"

    def purge_expired(self, db) -> int:
        purgeable = db.get_purgeable_snapshots()
        purged = 0
        for snap in purgeable:
            filepath = Path(snap["filepath"])
            if filepath.exists():
                filepath.unlink()
                logger.info("Purged expired image: %s", filepath)
            db.delete_snapshot_record(snap["id"])
            purged += 1

        if purged:
            logger.info("Purged %d expired snapshots", purged)
        return purged

    def enforce_storage_limit(self) -> int:
        total_size = sum(f.stat().st_size for f in self.storage_dir.glob("*.jpg"))
        if total_size <= self.max_storage_bytes:
            return 0

        files = sorted(self.storage_dir.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
        freed = 0
        for f in files:
            if total_size <= self.max_storage_bytes:
                break
            size = f.stat().st_size
            f.unlink()
            total_size -= size
            freed += 1
            logger.info("Storage limit: deleted %s", f.name)

        return freed
