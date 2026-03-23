"""Tests for src/inference/detector.py"""

import sys
from unittest.mock import MagicMock, patch

import numpy as np

from inference.detector import Detection


class TestDetection:
    def test_center_calculation(self):
        det = Detection(label="fish", confidence=0.9, bbox=(100, 200, 300, 400))
        assert det.center == (200, 300)

    def test_area(self):
        det = Detection(label="fish", confidence=0.9, bbox=(0, 0, 100, 50))
        assert det.area == 5000

    def test_fields(self):
        det = Detection(label="plant", confidence=0.75, bbox=(10, 20, 30, 40))
        assert det.label == "plant"
        assert det.confidence == 0.75
        assert det.bbox == (10, 20, 30, 40)

    def test_center_zero_bbox(self):
        det = Detection(label="fish", confidence=0.5, bbox=(0, 0, 0, 0))
        assert det.center == (0, 0)
        assert det.area == 0


class TestFishDetector:
    """Test FishDetector by mocking pycoral and cv2 imports within methods."""

    def _make_pycoral_mocks(self, labels=None, input_size=(300, 300)):
        """Create properly connected pycoral mock hierarchy."""
        mock_common = MagicMock()
        mock_common.input_size.return_value = input_size

        mock_detect_mod = MagicMock()

        mock_adapters = MagicMock()
        mock_adapters.common = mock_common
        mock_adapters.detect = mock_detect_mod

        mock_edgetpu = MagicMock()
        mock_interpreter = MagicMock()
        mock_edgetpu.make_interpreter.return_value = mock_interpreter

        mock_dataset = MagicMock()
        mock_dataset.read_label_file.return_value = labels or {0: "fish", 1: "plant"}

        mock_utils = MagicMock()
        mock_utils.edgetpu = mock_edgetpu
        mock_utils.dataset = mock_dataset

        modules = {
            "pycoral": MagicMock(),
            "pycoral.adapters": mock_adapters,
            "pycoral.adapters.common": mock_common,
            "pycoral.adapters.detect": mock_detect_mod,
            "pycoral.utils": mock_utils,
            "pycoral.utils.edgetpu": mock_edgetpu,
            "pycoral.utils.dataset": mock_dataset,
        }
        return modules, mock_common, mock_detect_mod, mock_interpreter

    def test_load_labels_fallback(self, tmp_path):
        """Test plain-text label loading when pycoral is not available."""
        from inference.detector import FishDetector

        labels_file = tmp_path / "labels.txt"
        labels_file.write_text("fish\nplant\ndecoration\n")

        detector = FishDetector.__new__(FishDetector)
        detector.confidence_threshold = 0.5

        with patch.dict(sys.modules, {"pycoral": None, "pycoral.utils": None,
                                       "pycoral.utils.dataset": None}):
            labels = detector._load_labels(str(labels_file))

        assert labels == {0: "fish", 1: "plant", 2: "decoration"}

    def test_load_labels_pycoral(self):
        """Test label loading via pycoral."""
        modules, _, _, _ = self._make_pycoral_mocks(labels={0: "fish", 1: "plant"})

        from inference.detector import FishDetector

        detector = FishDetector.__new__(FishDetector)

        with patch.dict(sys.modules, modules):
            labels = detector._load_labels("fake.txt")

        assert labels == {0: "fish", 1: "plant"}

    def test_load_model(self):
        """Test Edge TPU interpreter loading."""
        modules, _, _, mock_interpreter = self._make_pycoral_mocks()

        from inference.detector import FishDetector

        detector = FishDetector.__new__(FishDetector)

        with patch.dict(sys.modules, modules):
            result = detector._load_model("fake.tflite")

        mock_interpreter.allocate_tensors.assert_called_once()
        assert result is mock_interpreter

    def test_get_input_size(self):
        """Test getting model input size."""
        modules, mock_common, _, _ = self._make_pycoral_mocks(input_size=(300, 300))

        from inference.detector import FishDetector

        detector = FishDetector.__new__(FishDetector)
        detector.interpreter = MagicMock()

        with patch.dict(sys.modules, modules):
            result = detector._get_input_size()

        assert result == (300, 300)

    def test_init(self, tmp_path):
        """Test full FishDetector initialization."""
        labels_file = tmp_path / "labels.txt"
        labels_file.write_text("fish\nplant\n")

        modules, _, _, _ = self._make_pycoral_mocks(
            labels={0: "fish", 1: "plant"}, input_size=(300, 300)
        )

        with patch.dict(sys.modules, modules):
            from inference.detector import FishDetector

            detector = FishDetector(
                model_path="fake.tflite",
                labels_path=str(labels_file),
            )

        assert detector.confidence_threshold == 0.5
        assert detector.input_size == (300, 300)
        assert detector.labels == {0: "fish", 1: "plant"}

    def test_detect(self):
        """Test running detection on a frame."""
        mock_det_obj = MagicMock()
        mock_det_obj.bbox.xmin = 10
        mock_det_obj.bbox.ymin = 20
        mock_det_obj.bbox.xmax = 100
        mock_det_obj.bbox.ymax = 200
        mock_det_obj.id = 0
        mock_det_obj.score = 0.95

        modules, mock_common, mock_detect_mod, _ = self._make_pycoral_mocks()
        mock_detect_mod.get_objects.return_value = [mock_det_obj]

        mock_cv2 = MagicMock()
        mock_cv2.cvtColor.return_value = np.zeros((300, 300, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((300, 300, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4
        modules["cv2"] = mock_cv2

        from inference.detector import FishDetector

        detector = FishDetector.__new__(FishDetector)
        detector.confidence_threshold = 0.5
        detector.labels = {0: "fish", 1: "plant"}
        detector.interpreter = MagicMock()
        detector.input_size = (300, 300)

        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch.dict(sys.modules, modules):
            results = detector.detect(fake_frame)

        assert len(results) == 1
        assert results[0].label == "fish"
        assert results[0].confidence == 0.95

    def test_detect_unknown_label(self):
        """Test detection with unknown class ID uses fallback label."""
        mock_det_obj = MagicMock()
        mock_det_obj.bbox.xmin = 0
        mock_det_obj.bbox.ymin = 0
        mock_det_obj.bbox.xmax = 100
        mock_det_obj.bbox.ymax = 100
        mock_det_obj.id = 99
        mock_det_obj.score = 0.7

        modules, _, mock_detect_mod, _ = self._make_pycoral_mocks()
        mock_detect_mod.get_objects.return_value = [mock_det_obj]

        mock_cv2 = MagicMock()
        mock_cv2.cvtColor.return_value = np.zeros((300, 300, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((300, 300, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4
        modules["cv2"] = mock_cv2

        from inference.detector import FishDetector

        detector = FishDetector.__new__(FishDetector)
        detector.confidence_threshold = 0.5
        detector.labels = {0: "fish"}
        detector.interpreter = MagicMock()
        detector.input_size = (300, 300)

        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch.dict(sys.modules, modules):
            results = detector.detect(fake_frame)

        assert results[0].label == "class_99"
