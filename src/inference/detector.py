"""
Fish detection using TensorFlow Lite with Edge TPU delegate.

Uses an SSD MobileNet or EfficientDet model compiled for the Edge TPU.
The model detects fish, decorations, plants, and other tank objects.

Model compilation (done on a dev machine, not on the Coral):
  edgetpu_compiler model.tflite
"""

import logging
from dataclasses import dataclass, field
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (xmin, ymin, xmax, ymax)
    center: Tuple[int, int] = field(init=False)

    def __post_init__(self):
        cx = (self.bbox[0] + self.bbox[2]) // 2
        cy = (self.bbox[1] + self.bbox[3]) // 2
        self.center = (cx, cy)

    @property
    def area(self) -> int:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


class FishDetector:
    def __init__(
        self,
        model_path: str = "models/detect_fish_edgetpu.tflite",
        labels_path: str = "models/labels.txt",
        confidence_threshold: float = 0.5,
    ):
        from pycoral.adapters import common
        from pycoral.utils.dataset import read_label_file
        from pycoral.utils.edgetpu import make_interpreter

        self.confidence_threshold = confidence_threshold
        self.labels = read_label_file(labels_path)
        logger.info("Loaded %d labels: %s", len(self.labels), list(self.labels.values()))

        self.interpreter = make_interpreter(model_path)
        self.interpreter.allocate_tensors()

        self.input_size = common.input_size(self.interpreter)
        logger.info(
            "Model loaded. Input size: %s. Edge TPU delegate active.",
            self.input_size,
        )

    def detect(self, frame: Any) -> List[Detection]:
        import cv2
        from pycoral.adapters import common, detect

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_frame, self.input_size)

        common.set_input(self.interpreter, resized)
        self.interpreter.invoke()

        raw_detections = detect.get_objects(
            self.interpreter,
            score_threshold=self.confidence_threshold,
        )

        h, w = frame.shape[:2]
        scale_x = w / self.input_size[0]
        scale_y = h / self.input_size[1]

        results: List[Detection] = []
        for d in raw_detections:
            bbox = d.bbox
            label = self.labels.get(d.id, f"class_{d.id}")
            results.append(
                Detection(
                    label=label,
                    confidence=float(d.score),
                    bbox=(
                        int(bbox.xmin * scale_x),
                        int(bbox.ymin * scale_y),
                        int(bbox.xmax * scale_x),
                        int(bbox.ymax * scale_y),
                    ),
                )
            )

        return results
