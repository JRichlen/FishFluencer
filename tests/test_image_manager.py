"""Tests for src/data/image_manager.py"""



from data.image_manager import ImageManager
from inference.detector import Detection


class TestImageManager:
    def test_init_creates_directory(self, tmp_path):
        storage = tmp_path / "snapshots"
        ImageManager(storage_dir=str(storage))
        assert storage.exists()

    def test_describe_frame_no_detections(self):
        mgr = ImageManager()
        result = mgr.describe_frame(None, [])
        assert result == "Empty tank view — no fish visible in frame."

    def test_describe_frame_with_detections(self):
        mgr = ImageManager()
        dets = [
            Detection(label="fish", confidence=0.95, bbox=(900, 500, 1000, 600)),
            Detection(label="plant", confidence=0.8, bbox=(100, 100, 200, 200)),
        ]
        result = mgr.describe_frame(None, dets)
        assert "fish" in result
        assert "plant" in result
        assert "confidence" in result

    def test_describe_position(self):
        mgr = ImageManager()
        assert mgr._describe_position(10, 10) == "top-left"
        assert mgr._describe_position(50, 50) == "middle-center"
        assert mgr._describe_position(90, 90) == "bottom-right"
        assert mgr._describe_position(50, 10) == "top-center"
        assert mgr._describe_position(10, 90) == "bottom-left"

    def test_purge_expired(self, tmp_path):
        from unittest.mock import MagicMock

        # Create a fake file
        fake_file = tmp_path / "old_snap.jpg"
        fake_file.write_text("fake")

        db = MagicMock()
        db.get_purgeable_snapshots.return_value = [
            {"id": 1, "filepath": str(fake_file)},
        ]

        mgr = ImageManager(storage_dir=str(tmp_path))
        purged = mgr.purge_expired(db)
        assert purged == 1
        assert not fake_file.exists()
        db.delete_snapshot_record.assert_called_once_with(1)

    def test_purge_expired_missing_file(self, tmp_path):
        from unittest.mock import MagicMock

        db = MagicMock()
        db.get_purgeable_snapshots.return_value = [
            {"id": 1, "filepath": str(tmp_path / "nonexistent.jpg")},
        ]

        mgr = ImageManager(storage_dir=str(tmp_path))
        purged = mgr.purge_expired(db)
        assert purged == 1
        db.delete_snapshot_record.assert_called_once_with(1)

    def test_purge_expired_none(self, tmp_path):
        from unittest.mock import MagicMock

        db = MagicMock()
        db.get_purgeable_snapshots.return_value = []

        mgr = ImageManager(storage_dir=str(tmp_path))
        purged = mgr.purge_expired(db)
        assert purged == 0

    def test_enforce_storage_limit_under(self, tmp_path):
        mgr = ImageManager(storage_dir=str(tmp_path), max_storage_mb=100.0)
        freed = mgr.enforce_storage_limit()
        assert freed == 0

    def test_enforce_storage_limit_over(self, tmp_path):
        # Create files exceeding limit
        mgr = ImageManager(storage_dir=str(tmp_path), max_storage_mb=0.001)  # ~1KB limit
        for i in range(3):
            f = tmp_path / f"img_{i}.jpg"
            f.write_bytes(b"x" * 1000)

        freed = mgr.enforce_storage_limit()
        assert freed > 0
        remaining = list(tmp_path.glob("*.jpg"))
        assert len(remaining) < 3
