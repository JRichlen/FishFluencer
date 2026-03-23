"""Tests for src/capture/camera.py"""

from unittest.mock import MagicMock, patch

import pytest

from capture.camera import FishCamera, FrameResult


class TestFrameResult:
    def test_dataclass_fields(self):
        result = FrameResult(frame="fake", timestamp=1.0, device_index=0)
        assert result.frame == "fake"
        assert result.timestamp == 1.0
        assert result.device_index == 0


class TestFishCamera:
    def test_init_defaults(self):
        cam = FishCamera()
        assert cam.device_index == 0
        assert cam.resolution == (1920, 1080)
        assert cam.fps == 15
        assert cam.warmup_seconds == 2.0
        assert cam._cap is None

    def test_init_custom(self):
        cam = FishCamera(device_index=1, resolution=[640, 480], fps=30, warmup_seconds=0.5)
        assert cam.device_index == 1
        assert cam.resolution == (640, 480)
        assert cam.fps == 30

    @patch("capture.camera.cv2")
    @patch("capture.camera.time")
    def test_open_success(self, mock_time, mock_cv2):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_V4L2 = 200
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        cam = FishCamera(warmup_seconds=0.1)
        cam.open()

        mock_cv2.VideoCapture.assert_called_once_with(0, 200)
        assert cam._cap is mock_cap

    @patch("capture.camera.cv2")
    def test_open_failure(self, mock_cv2):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_V4L2 = 200

        cam = FishCamera()
        with pytest.raises(RuntimeError, match="Cannot open camera"):
            cam.open()

    def test_capture_frame_not_opened(self):
        cam = FishCamera()
        with pytest.raises(RuntimeError, match="Camera not opened"):
            cam.capture_frame()

    def test_capture_frame_cap_closed(self):
        cam = FishCamera()
        cam._cap = MagicMock()
        cam._cap.isOpened.return_value = False
        with pytest.raises(RuntimeError, match="Camera not opened"):
            cam.capture_frame()

    def test_capture_frame_success(self):
        cam = FishCamera()
        cam._cap = MagicMock()
        cam._cap.isOpened.return_value = True
        cam._cap.read.return_value = (True, "frame_data")

        result = cam.capture_frame()
        assert result.frame == "frame_data"
        assert result.device_index == 0
        assert isinstance(result.timestamp, float)

    def test_capture_frame_failure(self):
        cam = FishCamera()
        cam._cap = MagicMock()
        cam._cap.isOpened.return_value = True
        cam._cap.read.return_value = (False, None)

        with pytest.raises(RuntimeError, match="Frame capture failed"):
            cam.capture_frame()

    @patch("capture.camera.cv2")
    def test_save_snapshot(self, mock_cv2, tmp_path):
        cam = FishCamera()
        cam._cap = MagicMock()
        cam._cap.isOpened.return_value = True
        cam._cap.read.return_value = (True, "frame_data")
        mock_cv2.IMWRITE_JPEG_QUALITY = 1

        filepath = cam.save_snapshot(tmp_path, prefix="test")
        assert filepath.parent == tmp_path
        assert filepath.name.startswith("test_")
        mock_cv2.imwrite.assert_called_once()

    def test_close(self):
        cam = FishCamera()
        mock_cap = MagicMock()
        cam._cap = mock_cap
        cam.close()
        mock_cap.release.assert_called_once()
        assert cam._cap is None

    def test_close_when_none(self):
        cam = FishCamera()
        cam.close()  # Should not raise

    @patch("capture.camera.cv2")
    @patch("capture.camera.time")
    def test_context_manager(self, mock_time, mock_cv2):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_V4L2 = 200
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        with FishCamera(warmup_seconds=0) as cam:
            assert cam._cap is not None

        mock_cap.release.assert_called_once()
