"""ImageManager — describe_frame text, expired-image purge."""

import time
from dataclasses import dataclass, field

from src.data.db import FishDB
from src.data.image_manager import ImageManager


@dataclass
class FakeDet:
    label: str
    confidence: float
    center: tuple = field(default=(960, 540))


def test_describe_frame_empty(tmp_path):
    mgr = ImageManager(storage_dir=str(tmp_path / "snaps"))
    assert "Empty tank view" in mgr.describe_frame(None, [])


def test_describe_frame_positions(tmp_path):
    mgr = ImageManager(storage_dir=str(tmp_path / "snaps"))
    desc = mgr.describe_frame(
        None,
        [FakeDet("betta", 0.9, (200, 800))],
    )
    assert "betta" in desc
    assert "bottom" in desc
    assert "left" in desc


def test_purge_expired(tmp_path):
    storage = tmp_path / "snaps"
    storage.mkdir()
    img = storage / "old.jpg"
    img.write_bytes(b"fake")

    db = FishDB(str(tmp_path / "test.db"))
    # Register the snapshot with a purge_after in the past (already expired)
    with db._conn() as conn:
        conn.execute(
            "INSERT INTO snapshots (timestamp, filepath, description, purge_after) "
            "VALUES (?, ?, ?, ?)",
            (time.time() - 7200, str(img), "old", time.time() - 3600),
        )

    mgr = ImageManager(storage_dir=str(storage))
    purged = mgr.purge_expired(db)
    assert purged == 1
    assert not img.exists()
