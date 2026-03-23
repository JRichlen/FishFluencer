"""
Frame capture from Arducam IMX291 via OpenCV.
The IMX291 is a low-light sensor — ideal for tank lighting conditions.
Connected through the Syntech USB-C adapter to the Coral Dev Board.
"""

import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    frame: Any  # np.ndarray
    timestamp: float
    device_index: int


class FishCamera:
    def __init__(
        self,
        device_index: int = 0,
        resolution: tuple = (1920, 1080),
        fps: int = 15,
        warmup_seconds: float = 2.0,
    ):
        self.device_index = device_index
        self.resolution = tuple(resolution)
        self.fps = fps
        self.warmup_seconds = warmup_seconds
        self._cap: Optional[Any] = None

    def open(self) -> None:
        """Initialize camera with V4L2 backend (Linux)."""
        import cv2

        self._cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera at index {self.device_index}. "
                "Check USB connection via Syntech adapter."
            )

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        logger.info("Camera warmup (%ss)...", self.warmup_seconds)
        time.sleep(self.warmup_seconds)
        logger.info("Camera ready.")

    def capture_frame(self) -> FrameResult:
        """Grab a single frame."""
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError("Camera not opened. Call open() first.")

        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError("Frame capture failed — camera may be disconnected.")

        return FrameResult(
            frame=frame,
            timestamp=time.time(),
            device_index=self.device_index,
        )

    def save_snapshot(self, output_dir: Path, prefix: str = "snapshot") -> Path:
        """Capture and save a single JPEG locally. Returns file path."""
        import cv2

        result = self.capture_frame()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{int(result.timestamp)}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), result.frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        logger.info("Snapshot saved: %s", filepath)
        return filepath

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
