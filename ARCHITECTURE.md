# AI Fish Monitor & Social Media Poster — "FishFluencer"

## Project Overview

A privacy-first, edge-AI fish surveillance system running on a **Google Coral Edge TPU Dev Board**. The system uses on-device TensorFlow Lite models to detect, classify, and track fish behavior in real time, then generates text-only behavioral summaries that are sent to the Claude API to craft cheeky social media posts — as if written by the fish themselves.

**No images ever leave the device.** Photos are used locally for inference and display, described in text, then auto-purged on a configurable schedule.

The entire application is **remotely updatable via GitHub** with no SSH, VPN, or port forwarding required. Error logs push to the repo and can trigger GitHub-based coding agents for automated fix proposals (humans still approve and merge).

---

## Hardware Bill of Materials

| Component | Role | Interface |
|---|---|---|
| Google Coral Dev Board (Mendel Linux) | Main compute + Edge TPU inference | — |
| Arducam 1080P IMX291 | Camera capture (low-light optimized) | USB via Syntech adapter |
| DS18B20 Temperature Sensor | Water temp monitoring | GPIO pin 4 (1-Wire) |
| Hamityson 7" Mini HDMI Display | Local dashboard / status UI | Mini HDMI |
| Syntech USB-C to USB Adapter | Camera → Dev Board connection | USB-C port |
| MicroSD Card (≥32GB recommended) | OS + application storage | MicroSD slot |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORAL DEV BOARD (ON-DEVICE)                  │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐     │
│  │ Arducam  │───▶│ Frame Capture│───▶│ Edge TPU Inference│     │
│  │ IMX291   │    │ (OpenCV)     │    │ (TFLite + Coral)  │     │
│  └──────────┘    └──────────────┘    └────────┬──────────┘     │
│                                               │                 │
│  ┌──────────┐    ┌──────────────┐    ┌────────▼──────────┐     │
│  │ DS18B20  │───▶│ Temp Reader  │───▶│ Behavior Tracker  │     │
│  │ Sensor   │    │ (1-Wire)     │    │ (SQLite + Logic)  │     │
│  └──────────┘    └──────────────┘    └────────┬──────────┘     │
│                                               │                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Orchestrator (cron)                      │  │
│  │                                                          │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Text Summary │  │ Claude API   │  │ Post Publisher │  │  │
│  │  │ Generator    │─▶│ (text only!) │─▶│ (API calls)    │  │  │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Local HDMI   │  │ Image Purge  │  │ GitHub Sync Agent  │   │
│  │ Dashboard    │  │ (cron)       │  │ (pull + log push)  │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure (GitHub Repo)

```
fishfluencer/
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       ├── auto-fix.yml            # Triggers coding agent on error logs
│       └── lint-and-test.yml       # CI for PRs
├── config/
│   ├── default.yaml                # Default configuration
│   ├── fish_profiles.yaml          # Named fish characters + personalities
│   └── schedules.yaml              # Posting times, purge intervals, sync freq
├── models/
│   ├── detect_fish_edgetpu.tflite  # Compiled Edge TPU fish detection model
│   ├── labels.txt                  # Class labels
│   └── README.md                   # Model provenance + training notes
├── src/
│   ├── __init__.py
│   ├── main.py                     # Entry point + orchestrator
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── camera.py               # OpenCV frame capture from Arducam
│   │   └── temperature.py          # DS18B20 1-Wire reader
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── detector.py             # Edge TPU object detection
│   │   ├── tracker.py              # Multi-object tracking (centroid/SORT)
│   │   └── behavior.py             # Behavior classification from tracks
│   ├── data/
│   │   ├── __init__.py
│   │   ├── db.py                   # SQLite schema + queries
│   │   ├── summarizer.py           # Text summary from behavior logs
│   │   └── image_manager.py        # Local image storage + auto-purge
│   ├── social/
│   │   ├── __init__.py
│   │   ├── post_generator.py       # Claude API caller (text-only payloads)
│   │   ├── publisher.py            # Platform API adapters (X, Bluesky, etc.)
│   │   └── templates.py            # Prompt templates for Claude
│   ├── display/
│   │   ├── __init__.py
│   │   └── dashboard.py            # HDMI local display (Flask or PyGame)
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── github_sync.py          # Git pull agent for OTA updates
│   │   └── log_pusher.py           # Error log push to repo
│   └── utils/
│       ├── __init__.py
│       ├── config.py               # YAML config loader with env overrides
│       └── logging.py              # Structured logging
├── scripts/
│   ├── setup.sh                    # First-time device setup
│   ├── install_deps.sh             # Python + system dependency installer
│   └── register_services.sh        # systemd service registration
├── systemd/
│   ├── fishfluencer.service        # Main application service
│   ├── fishfluencer-sync.timer     # GitHub sync timer (every 15 min)
│   ├── fishfluencer-sync.service   # GitHub sync service
│   ├── fishfluencer-purge.timer    # Image purge timer
│   └── fishfluencer-purge.service  # Image purge service
├── dashboard/
│   └── templates/
│       └── index.html              # Local HDMI dashboard UI
├── tests/
│   ├── test_detector.py
│   ├── test_tracker.py
│   ├── test_summarizer.py
│   └── test_post_generator.py
├── logs/                           # .gitignore'd locally
│   └── .gitkeep
├── error_reports/                  # Pushed to repo on failure
│   └── .gitkeep
├── requirements.txt
└── pyproject.toml
```

---

## Module Deep Dives

### 1. Camera Capture (`src/capture/camera.py`)

```python
"""
Frame capture from Arducam IMX291 via OpenCV.
The IMX291 is a low-light sensor — ideal for tank lighting conditions.
Connected through the Syntech USB-C adapter to the Coral Dev Board.
"""

import cv2
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    frame: any  # np.ndarray
    timestamp: float
    device_index: int


class FishCamera:
    def __init__(
        self,
        device_index: int = 0,
        resolution: tuple[int, int] = (1920, 1080),
        fps: int = 15,
        warmup_seconds: float = 2.0,
    ):
        self.device_index = device_index
        self.resolution = resolution
        self.fps = fps
        self.warmup_seconds = warmup_seconds
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        """Initialize camera with V4L2 backend (Linux)."""
        self._cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera at index {self.device_index}. "
                "Check USB connection via Syntech adapter."
            )

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # IMX291 needs a brief warmup for auto-exposure to stabilize
        logger.info(f"Camera warmup ({self.warmup_seconds}s)...")
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
        result = self.capture_frame()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{int(result.timestamp)}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), result.frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        logger.info(f"Snapshot saved: {filepath}")
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
```

---

### 2. Temperature Sensor (`src/capture/temperature.py`)

```python
"""
DS18B20 1-Wire temperature sensor reader.

Wiring on Coral Dev Board:
  - VCC  → 3.3V pin
  - GND  → GND pin
  - DATA → GPIO pin 4 (with 4.7kΩ pull-up to 3.3V)

Prerequisites (run once):
  sudo modprobe w1-gpio
  sudo modprobe w1-therm
  # Or add to /etc/modules for persistence
"""

import time
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

W1_DEVICES_PATH = Path("/sys/bus/w1/devices")


@dataclass
class TempReading:
    celsius: float
    fahrenheit: float
    timestamp: float
    sensor_id: str


class DS18B20:
    def __init__(self, sensor_id: str | None = None):
        """
        Initialize with a specific sensor ID, or auto-detect the first one.
        Sensor IDs look like '28-xxxxxxxxxxxx'.
        """
        if sensor_id:
            self.sensor_path = W1_DEVICES_PATH / sensor_id / "w1_slave"
        else:
            self.sensor_path = self._auto_detect()

        self.sensor_id = self.sensor_path.parent.name
        logger.info(f"DS18B20 initialized: {self.sensor_id}")

    def _auto_detect(self) -> Path:
        """Find the first DS18B20 sensor on the 1-Wire bus."""
        candidates = list(W1_DEVICES_PATH.glob("28-*/w1_slave"))
        if not candidates:
            raise FileNotFoundError(
                "No DS18B20 found. Check wiring and ensure w1-gpio module is loaded."
            )
        return candidates[0]

    def read(self) -> TempReading:
        """Read current temperature. Blocks ~750ms per read (sensor conversion time)."""
        raw = self.sensor_path.read_text()
        lines = raw.strip().split("\n")

        # First line ends with YES if CRC check passed
        if not lines[0].strip().endswith("YES"):
            raise IOError(f"CRC check failed for sensor {self.sensor_id}")

        # Second line contains t=<millidegrees>
        temp_str = lines[1].split("t=")[1]
        celsius = int(temp_str) / 1000.0
        fahrenheit = celsius * 9.0 / 5.0 + 32.0

        return TempReading(
            celsius=round(celsius, 2),
            fahrenheit=round(fahrenheit, 2),
            timestamp=time.time(),
            sensor_id=self.sensor_id,
        )
```

---

### 3. Edge TPU Inference (`src/inference/detector.py`)

```python
"""
Fish detection using TensorFlow Lite with Edge TPU delegate.

Uses a SSD MobileNet or EfficientDet model compiled for the Edge TPU.
The model detects fish, decorations, plants, and other tank objects.

Model compilation (done on a dev machine, not on the Coral):
  edgetpu_compiler model.tflite

The compiled *_edgetpu.tflite file is what runs on the Coral.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pycoral.adapters import common, detect
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.dataset import read_label_file

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (xmin, ymin, xmax, ymax)
    center: tuple[int, int] = field(init=False)

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
        self.confidence_threshold = confidence_threshold

        # Load labels
        self.labels = read_label_file(labels_path)
        logger.info(f"Loaded {len(self.labels)} labels: {list(self.labels.values())}")

        # Initialize Edge TPU interpreter
        self.interpreter = make_interpreter(model_path)
        self.interpreter.allocate_tensors()

        # Cache input tensor details
        self.input_size = common.input_size(self.interpreter)
        logger.info(
            f"Model loaded. Input size: {self.input_size}. "
            f"Edge TPU delegate active."
        )

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Run detection on a single BGR frame (from OpenCV).
        Returns list of Detection objects above the confidence threshold.
        """
        import cv2

        # Resize to model input dimensions
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_frame, self.input_size)

        # Run inference on Edge TPU
        common.set_input(self.interpreter, resized)
        self.interpreter.invoke()

        # Parse results
        raw_detections = detect.get_objects(
            self.interpreter,
            score_threshold=self.confidence_threshold,
        )

        # Scale bounding boxes back to original frame dimensions
        h, w = frame.shape[:2]
        scale_x = w / self.input_size[0]
        scale_y = h / self.input_size[1]

        results: list[Detection] = []
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
```

---

### 4. Fish Tracker (`src/inference/tracker.py`)

```python
"""
Multi-object centroid tracker for persistent fish identity across frames.

Assigns stable IDs to detected fish so we can track individual movement
patterns over time. Uses a simple centroid-distance approach — upgrade
to DeepSORT if you need re-identification after occlusion.
"""

import math
import logging
from collections import OrderedDict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TrackedFish:
    fish_id: int
    label: str
    center: tuple[int, int]
    bbox: tuple[int, int, int, int]
    frames_tracked: int = 0
    frames_missing: int = 0
    trajectory: list[tuple[int, int]] = field(default_factory=list)

    @property
    def total_distance(self) -> float:
        """Total pixel distance traveled."""
        if len(self.trajectory) < 2:
            return 0.0
        dist = 0.0
        for i in range(1, len(self.trajectory)):
            x1, y1 = self.trajectory[i - 1]
            x2, y2 = self.trajectory[i]
            dist += math.hypot(x2 - x1, y2 - y1)
        return dist

    @property
    def zone(self) -> str:
        """Approximate tank zone based on vertical position (for behavior)."""
        _, y = self.center
        # Assuming 1080p: top third, middle, bottom third
        if y < 360:
            return "surface"
        elif y < 720:
            return "midwater"
        else:
            return "bottom"


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
        self._tracked: OrderedDict[int, TrackedFish] = OrderedDict()

    @property
    def active_fish(self) -> list[TrackedFish]:
        return list(self._tracked.values())

    def update(self, detections: list) -> list[TrackedFish]:
        """
        Match new detections to existing tracks using centroid distance.
        Returns the current set of actively tracked fish.
        """
        if not detections:
            # Mark all as missing
            to_remove = []
            for fish_id, fish in self._tracked.items():
                fish.frames_missing += 1
                if fish.frames_missing > self.max_missing_frames:
                    to_remove.append(fish_id)
            for fid in to_remove:
                logger.debug(f"Fish #{fid} deregistered (missing too long)")
                del self._tracked[fid]
            return self.active_fish

        det_centers = [d.center for d in detections]

        if not self._tracked:
            # Register all as new
            for det in detections:
                self._register(det)
            return self.active_fish

        # Compute distance matrix: existing tracks × new detections
        track_ids = list(self._tracked.keys())
        track_centers = [self._tracked[tid].center for tid in track_ids]

        distances = []
        for tc in track_centers:
            row = [math.hypot(tc[0] - dc[0], tc[1] - dc[1]) for dc in det_centers]
            distances.append(row)

        # Greedy matching (closest first)
        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        # Flatten and sort by distance
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
            # Update track
            fish = self._tracked[track_ids[ti]]
            fish.center = detections[di].center
            fish.bbox = detections[di].bbox
            fish.label = detections[di].label
            fish.frames_tracked += 1
            fish.frames_missing = 0
            fish.trajectory.append(fish.center)
            if len(fish.trajectory) > self.trajectory_length:
                fish.trajectory.pop(0)

            matched_tracks.add(ti)
            matched_dets.add(di)

        # Handle unmatched tracks
        for ti in range(len(track_ids)):
            if ti not in matched_tracks:
                fish = self._tracked[track_ids[ti]]
                fish.frames_missing += 1

        # Remove stale tracks
        to_remove = [
            tid
            for tid, fish in self._tracked.items()
            if fish.frames_missing > self.max_missing_frames
        ]
        for tid in to_remove:
            del self._tracked[tid]

        # Register unmatched detections as new fish
        for di in range(len(detections)):
            if di not in matched_dets:
                self._register(detections[di])

        return self.active_fish

    def _register(self, detection) -> None:
        fish = TrackedFish(
            fish_id=self._next_id,
            label=detection.label,
            center=detection.center,
            bbox=detection.bbox,
            trajectory=[detection.center],
        )
        self._tracked[self._next_id] = fish
        logger.debug(f"New fish registered: #{self._next_id} ({detection.label})")
        self._next_id += 1
```

---

### 5. Behavior Analyzer (`src/inference/behavior.py`)

```python
"""
Classify fish behavior from tracking data.

Takes trajectories + detection metadata and produces human-readable
behavior labels used in the text summaries sent to Claude.
"""

import math
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Behavior(str, Enum):
    RESTING = "resting"
    CRUISING = "cruising"
    DARTING = "darting"
    SURFACE_BREATHING = "surface_breathing"
    BOTTOM_DWELLING = "bottom_dwelling"
    GLASS_SURFING = "glass_surfing"
    FEEDING = "feeding"
    HIDING = "hiding"
    SCHOOLING = "schooling"
    TERRITORIAL = "territorial"
    UNKNOWN = "unknown"


@dataclass
class BehaviorEvent:
    fish_id: int
    fish_label: str
    behavior: Behavior
    confidence: float
    zone: str
    duration_frames: int
    description: str  # Human-readable for Claude prompt


class BehaviorAnalyzer:
    """
    Rule-based behavior classifier. Upgrade path: train a small
    classification head on Edge TPU for learned behavior detection.
    """

    def __init__(
        self,
        darting_speed_threshold: float = 40.0,   # px/frame
        resting_speed_threshold: float = 2.0,     # px/frame
        glass_surf_edge_margin: int = 80,          # px from frame edge
        frame_width: int = 1920,
        frame_height: int = 1080,
        min_behavior_frames: int = 10,
    ):
        self.darting_speed = darting_speed_threshold
        self.resting_speed = resting_speed_threshold
        self.edge_margin = glass_surf_edge_margin
        self.frame_w = frame_width
        self.frame_h = frame_height
        self.min_frames = min_behavior_frames

    def analyze(self, tracked_fish: list) -> list[BehaviorEvent]:
        """Classify behavior for each tracked fish."""
        events: list[BehaviorEvent] = []

        for fish in tracked_fish:
            if fish.frames_tracked < self.min_frames:
                continue

            behavior, confidence, description = self._classify(fish)
            events.append(
                BehaviorEvent(
                    fish_id=fish.fish_id,
                    fish_label=fish.label,
                    behavior=behavior,
                    confidence=confidence,
                    zone=fish.zone,
                    duration_frames=fish.frames_tracked,
                    description=description,
                )
            )

        return events

    def _classify(self, fish) -> tuple[Behavior, float, str]:
        traj = fish.trajectory
        if len(traj) < 2:
            return Behavior.UNKNOWN, 0.0, "Not enough data"

        # Calculate recent speeds (last N frames)
        window = min(30, len(traj))
        recent = traj[-window:]
        speeds = []
        for i in range(1, len(recent)):
            dx = recent[i][0] - recent[i - 1][0]
            dy = recent[i][1] - recent[i - 1][1]
            speeds.append(math.hypot(dx, dy))

        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0

        # Check for darting (sudden burst)
        if max_speed > self.darting_speed:
            return (
                Behavior.DARTING,
                min(max_speed / (self.darting_speed * 2), 1.0),
                f"{fish.label} made a sudden dart across the tank "
                f"(peak speed: {max_speed:.0f}px/frame)",
            )

        # Check for glass surfing (repeatedly near edges)
        edge_count = sum(
            1
            for x, y in recent
            if x < self.edge_margin
            or x > self.frame_w - self.edge_margin
        )
        if edge_count > len(recent) * 0.6:
            return (
                Behavior.GLASS_SURFING,
                edge_count / len(recent),
                f"{fish.label} is glass surfing — swimming back and forth "
                f"along the tank wall",
            )

        # Check for surface breathing
        if fish.zone == "surface" and avg_speed < self.resting_speed * 3:
            return (
                Behavior.SURFACE_BREATHING,
                0.7,
                f"{fish.label} is hanging near the surface, possibly gulping air",
            )

        # Check for resting
        if avg_speed < self.resting_speed:
            return (
                Behavior.RESTING,
                1.0 - (avg_speed / self.resting_speed),
                f"{fish.label} is resting near the {fish.zone} of the tank",
            )

        # Default: cruising
        return (
            Behavior.CRUISING,
            0.8,
            f"{fish.label} is cruising through the {fish.zone} "
            f"at a relaxed pace",
        )
```

---

### 6. Database & Summary (`src/data/db.py`)

```python
"""
SQLite database for behavior logs, temperature readings, and post history.
All data stays on-device.
"""

import sqlite3
import time
import json
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS behavior_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    fish_id INTEGER NOT NULL,
    fish_label TEXT NOT NULL,
    behavior TEXT NOT NULL,
    zone TEXT NOT NULL,
    confidence REAL NOT NULL,
    description TEXT NOT NULL,
    duration_frames INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS temperature_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    celsius REAL NOT NULL,
    fahrenheit REAL NOT NULL,
    sensor_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    filepath TEXT NOT NULL,
    description TEXT,
    purge_after REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    summary_used TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_behavior_ts ON behavior_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_temp_ts ON temperature_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_snap_purge ON snapshots(purge_after);
"""


class FishDB:
    def __init__(self, db_path: str = "data/fishfluencer.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def log_behavior(self, event) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO behavior_log
                   (timestamp, fish_id, fish_label, behavior, zone,
                    confidence, description, duration_frames)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(), event.fish_id, event.fish_label,
                    event.behavior.value, event.zone, event.confidence,
                    event.description, event.duration_frames,
                ),
            )

    def log_temperature(self, reading) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO temperature_log
                   (timestamp, celsius, fahrenheit, sensor_id)
                   VALUES (?, ?, ?, ?)""",
                (reading.timestamp, reading.celsius,
                 reading.fahrenheit, reading.sensor_id),
            )

    def register_snapshot(
        self, filepath: str, description: str, purge_hours: float = 24.0
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO snapshots
                   (timestamp, filepath, description, purge_after)
                   VALUES (?, ?, ?, ?)""",
                (time.time(), filepath, description,
                 time.time() + purge_hours * 3600),
            )

    def get_purgeable_snapshots(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, filepath FROM snapshots WHERE purge_after < ?",
                (time.time(),),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_snapshot_record(self, snap_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM snapshots WHERE id = ?", (snap_id,))

    def get_behavior_summary(self, hours: float = 12.0) -> list[dict]:
        """Get behavior events from the last N hours for summary generation."""
        since = time.time() - hours * 3600
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT fish_label, behavior, zone, description,
                          COUNT(*) as event_count,
                          AVG(confidence) as avg_confidence
                   FROM behavior_log
                   WHERE timestamp > ?
                   GROUP BY fish_label, behavior
                   ORDER BY event_count DESC""",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_temps(self, hours: float = 12.0) -> list[dict]:
        since = time.time() - hours * 3600
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT AVG(fahrenheit) as avg_f, MIN(fahrenheit) as min_f,
                          MAX(fahrenheit) as max_f, COUNT(*) as readings
                   FROM temperature_log WHERE timestamp > ?""",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]
```

---

### 7. Text Summary Generator (`src/data/summarizer.py`)

```python
"""
Generates text-only summaries from behavior logs and sensor data.

THIS IS THE PRIVACY BOUNDARY. Only text leaves the device — never images.
The summaries are what get sent to the Claude API for post generation.
"""

import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BehaviorSummarizer:
    def __init__(self, db, fish_profiles: dict):
        """
        Args:
            db: FishDB instance
            fish_profiles: Dict mapping fish labels to character profiles.
                Example: {"betta": {"name": "Sir Bubbles", "personality": "dramatic diva"}}
        """
        self.db = db
        self.profiles = fish_profiles

    def generate_summary(self, hours: float = 12.0) -> str:
        """
        Build a text summary of recent fish activity for the Claude prompt.
        No image data is included — only behavioral descriptions and stats.
        """
        behaviors = self.db.get_behavior_summary(hours=hours)
        temps = self.db.get_recent_temps(hours=hours)
        now = datetime.now()

        lines = [
            f"=== Fish Tank Status Report ===",
            f"Generated: {now.strftime('%A, %B %d at %I:%M %p')}",
            f"Reporting window: last {hours:.0f} hours",
            "",
        ]

        # Temperature context
        if temps and temps[0]["readings"]:
            t = temps[0]
            lines.append(f"Water temperature: {t['avg_f']:.1f}°F "
                         f"(range: {t['min_f']:.1f}–{t['max_f']:.1f}°F)")
            lines.append("")

        # Per-fish behavior narrative
        if not behaviors:
            lines.append("No fish activity detected in this period.")
        else:
            lines.append("=== Fish Activity ===")
            for b in behaviors:
                label = b["fish_label"]
                profile = self.profiles.get(label, {})
                name = profile.get("name", label.title())
                personality = profile.get("personality", "mysterious")

                lines.append(
                    f"\n{name} (a {personality} {label}):"
                    f"\n  - Primary behavior: {b['behavior']} "
                    f"(observed {b['event_count']}x, "
                    f"avg confidence: {b['avg_confidence']:.0%})"
                    f"\n  - Zone: {b['zone']}"
                    f"\n  - Detail: {b['description']}"
                )

        # Snapshot descriptions (text only — file paths are NOT included)
        snap_descriptions = self._get_snapshot_descriptions(hours)
        if snap_descriptions:
            lines.append("\n=== Scene Descriptions (from local images) ===")
            for desc in snap_descriptions:
                lines.append(f"  - {desc}")

        return "\n".join(lines)

    def _get_snapshot_descriptions(self, hours: float) -> list[str]:
        """Return text descriptions of recent snapshots. NOT file paths."""
        since = time.time() - hours * 3600
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT description FROM snapshots "
                "WHERE timestamp > ? AND description IS NOT NULL "
                "ORDER BY timestamp DESC LIMIT 10",
                (since,),
            ).fetchall()
            return [r["description"] for r in rows]
```

---

### 8. Image Manager with Auto-Purge (`src/data/image_manager.py`)

```python
"""
Local image lifecycle management.

PRIVACY GUARANTEES:
  1. Images are stored ONLY in a local directory on the microSD card
  2. Images are NEVER transmitted over any network interface
  3. Images are auto-deleted after the configured retention period
  4. Only text descriptions derived from images leave the device
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
        """
        Generate a text description of a frame from its detections.
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
        """Convert pixel percentages to natural language position."""
        v = "top" if y_pct < 33 else "middle" if y_pct < 66 else "bottom"
        h = "left" if x_pct < 33 else "center" if x_pct < 66 else "right"
        return f"{v}-{h}"

    def purge_expired(self, db) -> int:
        """Delete expired images from disk and database."""
        purgeable = db.get_purgeable_snapshots()
        purged = 0
        for snap in purgeable:
            filepath = Path(snap["filepath"])
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Purged expired image: {filepath}")
            db.delete_snapshot_record(snap["id"])
            purged += 1

        if purged:
            logger.info(f"Purged {purged} expired snapshots")
        return purged

    def enforce_storage_limit(self) -> int:
        """Delete oldest images if storage exceeds limit."""
        total_size = sum(f.stat().st_size for f in self.storage_dir.glob("*.jpg"))
        if total_size <= self.max_storage_bytes:
            return 0

        # Sort oldest first and delete until under limit
        files = sorted(self.storage_dir.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
        freed = 0
        for f in files:
            if total_size <= self.max_storage_bytes:
                break
            size = f.stat().st_size
            f.unlink()
            total_size -= size
            freed += 1
            logger.info(f"Storage limit: deleted {f.name}")

        return freed
```

---

### 9. Social Media Post Generator (`src/social/post_generator.py`)

```python
"""
Claude API integration for generating social media posts.

CRITICAL PRIVACY RULE: Only TEXT is sent to the API. Never image data,
file paths, base64, or any binary content. The summarizer module handles
converting visual observations into text descriptions.
"""

import json
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


class PostGenerator:
    def __init__(
        self,
        api_key: str,
        fish_profiles: dict,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 300,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.fish_profiles = fish_profiles
        self._client = httpx.Client(timeout=30.0)

    def generate_post(
        self,
        summary: str,
        platform: str = "twitter",
        character_name: str | None = None,
    ) -> str:
        """
        Generate a social media post from a text-only behavior summary.

        Args:
            summary: Text summary from BehaviorSummarizer (no images!)
            platform: Target platform for length/style calibration
            character_name: Which fish character should "write" the post
        """
        char_context = ""
        if character_name and character_name in self.fish_profiles:
            profile = self.fish_profiles[character_name]
            char_context = (
                f"You are posting as '{character_name}', a {profile['personality']} "
                f"{profile.get('species', 'fish')}. "
                f"Quirks: {profile.get('quirks', 'none specified')}. "
            )

        platform_rules = {
            "twitter": "Keep it under 280 characters. Hashtags welcome.",
            "bluesky": "Keep it under 300 characters. Casual and fun.",
            "instagram": "Can be longer (up to 500 chars). Use emojis freely.",
            "mastodon": "Up to 500 characters. Be community-friendly.",
        }

        system_prompt = (
            "You are a ghostwriter for a pet fish's social media account. "
            "You write cheeky, funny first-person posts as if the fish is "
            "posting about their own day. The posts should be endearing, "
            "relatable, and occasionally reference fish-specific humor "
            "(tank life, water changes, the mysterious 'sky ceiling', "
            "the giant who feeds them, etc.). "
            f"{char_context}"
            f"\nPlatform: {platform}. {platform_rules.get(platform, '')}"
            "\n\nIMPORTANT: You are given a text summary of the fish's recent "
            "behavior and tank conditions. Use this to craft a post that "
            "references real events from the fish's day. Be creative but "
            "grounded in the actual observations."
        )

        response = self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Here is the fish tank activity summary:\n\n"
                            f"{summary}\n\n"
                            f"Write a single social media post for {platform}."
                        ),
                    }
                ],
            },
        )

        response.raise_for_status()
        data = response.json()

        # Extract text from response
        post_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                post_text += block["text"]

        logger.info(f"Generated {platform} post: {post_text[:80]}...")
        return post_text.strip()
```

---

### 10. GitHub OTA Sync Agent (`src/sync/github_sync.py`)

```python
"""
OTA update system via GitHub repository sync.

How it works:
  1. A systemd timer fires every N minutes
  2. This agent does a `git pull` from the configured remote
  3. If files changed, it optionally restarts the main service
  4. No SSH, VPN, or port-forwarding required — outbound HTTPS only

The device only needs outbound internet access to github.com.
Updates are pushed by developers to the repo; the device pulls them.
"""

import subprocess
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHubSyncAgent:
    def __init__(
        self,
        repo_dir: str = "/opt/fishfluencer",
        branch: str = "main",
        service_name: str = "fishfluencer.service",
        pre_update_script: str | None = None,
        post_update_script: str | None = "scripts/install_deps.sh",
    ):
        self.repo_dir = Path(repo_dir)
        self.branch = branch
        self.service_name = service_name
        self.pre_update_script = pre_update_script
        self.post_update_script = post_update_script

    def sync(self) -> dict:
        """
        Pull latest changes and restart service if needed.
        Returns a status dict for logging.
        """
        result = {
            "action": "sync",
            "changed": False,
            "restarted": False,
            "error": None,
        }

        try:
            # Capture current HEAD
            old_hash = self._get_head_hash()

            # Fetch and pull
            self._run_git("fetch", "origin", self.branch)
            pull_output = self._run_git(
                "pull", "origin", self.branch, "--ff-only"
            )

            new_hash = self._get_head_hash()
            result["old_hash"] = old_hash[:8]
            result["new_hash"] = new_hash[:8]

            if old_hash != new_hash:
                result["changed"] = True
                logger.info(
                    f"Updated: {old_hash[:8]} → {new_hash[:8]}"
                )

                # Run post-update script (e.g., install new deps)
                if self.post_update_script:
                    script = self.repo_dir / self.post_update_script
                    if script.exists():
                        logger.info(f"Running post-update: {script}")
                        subprocess.run(
                            ["bash", str(script)],
                            cwd=str(self.repo_dir),
                            check=True,
                            timeout=120,
                        )

                # Restart the main service
                subprocess.run(
                    ["sudo", "systemctl", "restart", self.service_name],
                    check=True,
                    timeout=30,
                )
                result["restarted"] = True
                logger.info(f"Service {self.service_name} restarted.")
            else:
                logger.debug("Already up to date.")

        except subprocess.CalledProcessError as e:
            result["error"] = f"Command failed: {e.cmd} → {e.returncode}"
            logger.error(result["error"])
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Sync failed: {e}")

        return result

    def _get_head_hash(self) -> str:
        return self._run_git("rev-parse", "HEAD").strip()

    def _run_git(self, *args: str) -> str:
        cmd = ["git", "-C", str(self.repo_dir)] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=True
        )
        return result.stdout
```

---

### 11. Error Log Pusher (`src/sync/log_pusher.py`)

```python
"""
Push structured error reports to the GitHub repo for automated triage.

Flow:
  1. Unhandled exception or critical error occurs
  2. This module serializes a sanitized error report (no images, no secrets)
  3. Commits it to error_reports/ in the repo
  4. Pushes to a dedicated branch
  5. GitHub Actions workflow detects the new file and triggers a coding agent
  6. The agent analyzes the error, proposes a fix PR
  7. A human reviews and merges

The error report format is structured so coding agents can parse it.
"""

import json
import time
import traceback
import subprocess
import platform
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorLogPusher:
    def __init__(
        self,
        repo_dir: str = "/opt/fishfluencer",
        error_dir: str = "error_reports",
        remote_branch_prefix: str = "error-report",
    ):
        self.repo_dir = Path(repo_dir)
        self.error_dir = self.repo_dir / error_dir
        self.error_dir.mkdir(parents=True, exist_ok=True)
        self.branch_prefix = remote_branch_prefix

    def report_error(
        self,
        exception: Exception,
        context: dict | None = None,
    ) -> str | None:
        """
        Create and push a structured error report.
        Returns the branch name if successful, None if push failed.
        """
        timestamp = int(time.time())
        report_id = f"err_{timestamp}"
        branch_name = f"{self.branch_prefix}/{report_id}"

        report = {
            "report_id": report_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                ),
            },
            "system": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            },
            "context": self._sanitize_context(context or {}),
            "suggested_files": self._guess_relevant_files(exception),
        }

        # Write report file
        report_path = self.error_dir / f"{report_id}.json"
        report_path.write_text(json.dumps(report, indent=2))

        # Commit and push to a new branch
        try:
            self._git("checkout", "-b", branch_name)
            self._git("add", str(report_path.relative_to(self.repo_dir)))
            self._git(
                "commit", "-m",
                f"error-report: {type(exception).__name__} in "
                f"{self._extract_module(exception)}"
            )
            self._git("push", "origin", branch_name)
            logger.info(f"Error report pushed: {branch_name}")

            # Return to main branch
            self._git("checkout", "main")
            return branch_name

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push error report: {e}")
            # Clean up: return to main
            try:
                self._git("checkout", "main")
            except Exception:
                pass
            return None

    def _sanitize_context(self, context: dict) -> dict:
        """Strip any sensitive data (API keys, file paths to images, etc.)."""
        sanitized = {}
        sensitive_keys = {"api_key", "secret", "password", "token", "image", "frame"}
        for k, v in context.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 1000:
                sanitized[k] = v[:500] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized

    def _extract_module(self, exc: Exception) -> str:
        """Extract the module name from the traceback."""
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            return Path(tb[-1].filename).stem
        return "unknown"

    def _guess_relevant_files(self, exc: Exception) -> list[str]:
        """List source files from the traceback for the coding agent."""
        tb = traceback.extract_tb(exc.__traceback__)
        files = []
        for frame in tb:
            rel = Path(frame.filename)
            if "fishfluencer" in str(rel) or "src/" in str(rel):
                files.append(str(rel))
        return list(set(files))

    def _git(self, *args: str) -> str:
        cmd = ["git", "-C", str(self.repo_dir)] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=True
        )
        return result.stdout
```

---

### 12. Main Orchestrator (`src/main.py`)

```python
"""
FishFluencer main entry point.

Ties together all subsystems:
  - Camera capture
  - Edge TPU inference
  - Fish tracking + behavior analysis
  - Temperature monitoring
  - Text summary generation
  - Claude API post generation
  - Image lifecycle management
  - Error reporting
"""

import sys
import time
import signal
import logging
import schedule
import yaml
from pathlib import Path

from capture.camera import FishCamera
from capture.temperature import DS18B20
from inference.detector import FishDetector
from inference.tracker import CentroidTracker
from inference.behavior import BehaviorAnalyzer
from data.db import FishDB
from data.summarizer import BehaviorSummarizer
from data.image_manager import ImageManager
from social.post_generator import PostGenerator
from sync.log_pusher import ErrorLogPusher

logger = logging.getLogger("fishfluencer")


class FishFluencer:
    def __init__(self, config_path: str = "config/default.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Core components
        self.db = FishDB(self.config.get("db_path", "data/fishfluencer.db"))
        self.camera = FishCamera(**self.config.get("camera", {}))
        self.detector = FishDetector(**self.config.get("detector", {}))
        self.tracker = CentroidTracker(**self.config.get("tracker", {}))
        self.analyzer = BehaviorAnalyzer(**self.config.get("behavior", {}))
        self.temp_sensor = DS18B20(self.config.get("temp_sensor_id"))
        self.image_mgr = ImageManager(**self.config.get("images", {}))
        self.summarizer = BehaviorSummarizer(
            self.db, self.config.get("fish_profiles", {})
        )
        self.post_gen = PostGenerator(
            api_key=self.config["anthropic_api_key"],
            fish_profiles=self.config.get("fish_profiles", {}),
        )
        self.error_pusher = ErrorLogPusher(**self.config.get("error_reporting", {}))

        self._running = False

    def start(self):
        """Start the main processing loop and scheduled tasks."""
        logger.info("=== FishFluencer starting ===")
        self._running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        self.camera.open()

        # Schedule periodic tasks
        post_times = self.config.get("post_times", ["09:00", "17:00"])
        for t in post_times:
            schedule.every().day.at(t).do(self._generate_and_post)

        schedule.every(5).minutes.do(self._read_temperature)
        schedule.every(15).minutes.do(self._take_snapshot)
        schedule.every(1).hours.do(self._purge_images)

        # Main inference loop
        fps_target = self.config.get("inference_fps", 5)
        frame_interval = 1.0 / fps_target

        try:
            while self._running:
                loop_start = time.time()

                try:
                    self._process_frame()
                except Exception as e:
                    logger.error(f"Frame processing error: {e}")
                    self.error_pusher.report_error(
                        e, context={"phase": "frame_processing"}
                    )

                # Run any pending scheduled tasks
                schedule.run_pending()

                # Maintain target FPS
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            self.error_pusher.report_error(e, context={"phase": "main_loop"})
        finally:
            self.camera.close()
            logger.info("=== FishFluencer stopped ===")

    def _process_frame(self):
        """Capture → Detect → Track → Analyze (single frame)."""
        result = self.camera.capture_frame()
        detections = self.detector.detect(result.frame)
        tracked = self.tracker.update(detections)
        behaviors = self.analyzer.analyze(tracked)

        for event in behaviors:
            self.db.log_behavior(event)

    def _take_snapshot(self):
        """Save a snapshot with text description for later summarization."""
        result = self.camera.capture_frame()
        detections = self.detector.detect(result.frame)
        description = self.image_mgr.describe_frame(result.frame, detections)

        filepath = self.camera.save_snapshot(
            self.image_mgr.storage_dir, prefix="scheduled"
        )
        self.db.register_snapshot(
            str(filepath),
            description=description,
            purge_hours=self.config.get("image_retention_hours", 24.0),
        )

    def _read_temperature(self):
        """Read and log water temperature."""
        try:
            reading = self.temp_sensor.read()
            self.db.log_temperature(reading)
            logger.debug(f"Temp: {reading.fahrenheit}°F")
        except Exception as e:
            logger.warning(f"Temp read failed: {e}")

    def _generate_and_post(self):
        """Generate text summary → Claude API → publish post."""
        try:
            summary = self.summarizer.generate_summary(hours=12.0)
            logger.info(f"Summary generated ({len(summary)} chars)")

            platforms = self.config.get("platforms", ["twitter"])
            fish_name = self.config.get("primary_poster", None)

            for platform in platforms:
                post = self.post_gen.generate_post(
                    summary=summary,
                    platform=platform,
                    character_name=fish_name,
                )
                logger.info(f"[{platform}] Post: {post[:100]}...")

                # TODO: Wire up platform-specific publisher
                # publisher.publish(platform, post)

                self.db.log_post(platform, post, summary)

        except Exception as e:
            logger.error(f"Post generation failed: {e}")
            self.error_pusher.report_error(
                e, context={"phase": "post_generation"}
            )

    def _purge_images(self):
        """Delete expired images from disk."""
        self.image_mgr.purge_expired(self.db)
        self.image_mgr.enforce_storage_limit()

    def _shutdown(self, signum, frame):
        logger.info(f"Shutdown signal received ({signum})")
        self._running = False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    app = FishFluencer(config_path)
    app.start()
```

---

## Configuration (`config/default.yaml`)

```yaml
# === FishFluencer Configuration ===

# Anthropic API (text-only calls — never sends images)
anthropic_api_key: "${ANTHROPIC_API_KEY}"  # Set via environment variable

# Camera (Arducam IMX291 via USB)
camera:
  device_index: 0
  resolution: [1920, 1080]
  fps: 15
  warmup_seconds: 2.0

# Edge TPU Model
detector:
  model_path: "models/detect_fish_edgetpu.tflite"
  labels_path: "models/labels.txt"
  confidence_threshold: 0.5

# Tracker
tracker:
  max_missing_frames: 30
  max_distance: 120.0
  trajectory_length: 300

# Behavior analysis
behavior:
  darting_speed_threshold: 40.0
  resting_speed_threshold: 2.0
  glass_surf_edge_margin: 80
  frame_width: 1920
  frame_height: 1080

# Temperature sensor
temp_sensor_id: null  # Auto-detect first DS18B20

# Image privacy
images:
  storage_dir: "data/snapshots"
  retention_hours: 24.0       # Auto-delete after 24 hours
  max_storage_mb: 500.0       # Hard cap on snapshot disk usage

image_retention_hours: 24.0

# Inference loop
inference_fps: 5              # Frames per second for detection

# Social media posting schedule (24h format)
post_times:
  - "09:00"
  - "17:00"

# Target platforms
platforms:
  - twitter

# Fish character who "writes" the posts
primary_poster: "Sir Bubbles"

# Fish character profiles
fish_profiles:
  betta:
    name: "Sir Bubbles"
    species: "betta fish"
    personality: "dramatic diva with main character energy"
    quirks: >
      refers to the filter as 'the spa jets', calls food time
      'the daily feast from the sky giant', thinks the thermometer
      is a rival fish, dramatically flares at own reflection

# Database
db_path: "data/fishfluencer.db"

# Error reporting
error_reporting:
  repo_dir: "/opt/fishfluencer"
  error_dir: "error_reports"
  remote_branch_prefix: "error-report"
```

---

## GitHub Actions: Auto-Fix Workflow (`.github/workflows/auto-fix.yml`)

```yaml
name: Auto-Fix Error Reports

on:
  push:
    branches:
      - 'error-report/**'
    paths:
      - 'error_reports/*.json'

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  triage-and-fix:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
          fetch-depth: 0

      - name: Find new error report
        id: find_report
        run: |
          REPORT=$(git diff --name-only HEAD~1 HEAD -- 'error_reports/*.json' | head -1)
          echo "report_path=$REPORT" >> $GITHUB_OUTPUT
          echo "Found report: $REPORT"

      - name: Read error report
        id: read_report
        run: |
          CONTENT=$(cat "${{ steps.find_report.outputs.report_path }}")
          echo "report_content<<EOF" >> $GITHUB_OUTPUT
          echo "$CONTENT" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      # ──────────────────────────────────────────────────
      # OPTION A: Use Claude Code (via Anthropic's GitHub Action)
      # This uses Claude as a coding agent to analyze the error
      # and propose a fix automatically.
      # ──────────────────────────────────────────────────
      - name: Claude Code — Analyze and Fix
        uses: anthropics/claude-code-action@beta
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            An automated error report was filed from a FishFluencer device.
            Analyze this error and propose a minimal, targeted fix.

            Error report:
            ${{ steps.read_report.outputs.report_content }}

            Instructions:
            1. Read the traceback and identify the root cause
            2. Check the suggested_files for context
            3. Propose a fix as a new PR against main
            4. Include a clear PR description explaining the fix
            5. Do NOT modify config files or secrets
            6. Keep changes minimal and focused

      # ──────────────────────────────────────────────────
      # OPTION B: Open a GitHub Issue for human triage
      # (Use this if you prefer manual review over auto-fix)
      # ──────────────────────────────────────────────────
      # - name: Create Issue
      #   uses: actions/github-script@v7
      #   with:
      #     script: |
      #       const report = JSON.parse(process.env.REPORT_CONTENT);
      #       await github.rest.issues.create({
      #         owner: context.repo.owner,
      #         repo: context.repo.repo,
      #         title: `[Auto] ${report.error.type}: ${report.error.message.slice(0, 80)}`,
      #         body: `## Automated Error Report\n\n\`\`\`json\n${JSON.stringify(report, null, 2)}\n\`\`\``,
      #         labels: ['bug', 'auto-reported']
      #       });
```

---

## systemd Services

### Main Application (`systemd/fishfluencer.service`)

```ini
[Unit]
Description=FishFluencer AI Fish Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mendel
WorkingDirectory=/opt/fishfluencer
Environment=ANTHROPIC_API_KEY=sk-ant-xxxxx
ExecStart=/opt/fishfluencer/.venv/bin/python -m src.main config/default.yaml
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### GitHub Sync Timer (`systemd/fishfluencer-sync.timer`)

```ini
[Unit]
Description=FishFluencer GitHub Sync Timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

### GitHub Sync Service (`systemd/fishfluencer-sync.service`)

```ini
[Unit]
Description=FishFluencer GitHub Sync
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=mendel
WorkingDirectory=/opt/fishfluencer
ExecStart=/opt/fishfluencer/.venv/bin/python -c "from src.sync.github_sync import GitHubSyncAgent; GitHubSyncAgent().sync()"
StandardOutput=journal
StandardError=journal
```

### Image Purge Timer (`systemd/fishfluencer-purge.timer`)

```ini
[Unit]
Description=FishFluencer Image Purge Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Device Setup Script (`scripts/setup.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== FishFluencer Device Setup ==="

# --- System packages ---
sudo apt-get update
sudo apt-get install -y \
    python3-venv python3-pip \
    git \
    libopencv-dev python3-opencv \
    sqlite3 \
    v4l-utils \
    i2c-tools

# --- 1-Wire for DS18B20 ---
echo "Enabling 1-Wire interface..."
if ! grep -q "w1-gpio" /etc/modules; then
    echo "w1-gpio" | sudo tee -a /etc/modules
    echo "w1-therm" | sudo tee -a /etc/modules
fi
sudo modprobe w1-gpio || true
sudo modprobe w1-therm || true

# --- Clone or update repo ---
REPO_DIR="/opt/fishfluencer"
REPO_URL="https://github.com/YOUR_USER/fishfluencer.git"

if [ -d "$REPO_DIR" ]; then
    echo "Repo exists, pulling latest..."
    cd "$REPO_DIR"
    git pull origin main
else
    echo "Cloning repo..."
    sudo mkdir -p "$REPO_DIR"
    sudo chown mendel:mendel "$REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# --- Python virtual environment ---
echo "Setting up Python venv..."
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# --- PyCoral (Edge TPU runtime) ---
echo "Installing PyCoral..."
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y libedgetpu1-std python3-pycoral

# --- Git configuration for log pushing ---
echo "Configuring git for error log push..."
git config user.email "fishfluencer-device@local"
git config user.name "FishFluencer Device"

# --- Install systemd services ---
echo "Installing systemd services..."
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fishfluencer.service
sudo systemctl enable fishfluencer-sync.timer
sudo systemctl enable fishfluencer-purge.timer

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Set your API key:  sudo systemctl edit fishfluencer"
echo "     Add: Environment=ANTHROPIC_API_KEY=sk-ant-..."
echo "  2. Place your Edge TPU model in models/"
echo "  3. Edit config/fish_profiles.yaml with your fish characters"
echo "  4. Start:  sudo systemctl start fishfluencer"
echo "  5. Logs:   journalctl -u fishfluencer -f"
```

---

## Model Training Notes

The Edge TPU requires a **quantized TensorFlow Lite** model compiled with the Edge TPU compiler. Recommended approach:

1. **Start with a pre-trained model** — Use `ssd_mobilenet_v2` or `efficientdet-lite0` from TF Model Zoo
2. **Fine-tune on fish data** — Collect labeled images from your tank or use datasets like [Fish4Knowledge](http://groups.inf.ed.ac.uk/f4k/) or [DeepFish](https://alzayats.github.io/DeepFish/)
3. **Custom classes** — Train to detect your specific fish species plus tank objects (filter, heater, plants, decorations, food)
4. **Quantize** — Post-training quantization to INT8 (required for Edge TPU)
5. **Compile** — Run `edgetpu_compiler model.tflite` to produce the `_edgetpu.tflite` variant

A reasonable starting model can detect 5–10 object classes at ~30 FPS on the Edge TPU.

---

## Privacy Architecture Summary

| Data Type | Stays On-Device | Leaves Device (Text Only) |
|---|---|---|
| Raw camera frames | ✅ Processed in RAM | ❌ Never |
| Saved JPEG snapshots | ✅ Auto-purged after 24h | ❌ Never |
| Fish detection boxes | ✅ Stored in SQLite | ❌ Never |
| Behavior descriptions | ✅ Stored in SQLite | ✅ As text summary to Claude API |
| Temperature readings | ✅ Stored in SQLite | ✅ As text in summary |
| Social media posts | ✅ Logged in SQLite | ✅ Published to platforms |
| Error tracebacks | ✅ Logged locally | ✅ Sanitized JSON to GitHub |
| API keys / secrets | ✅ In systemd env only | ❌ Never in repo or logs |

---

## Extension Points

The system is designed to be extended by pushing code to the GitHub repo:

- **New fish characters** — Add to `config/fish_profiles.yaml`
- **New platforms** — Add a publisher adapter in `src/social/publisher.py`
- **New behaviors** — Add detection rules in `src/inference/behavior.py`
- **Dashboard widgets** — Update `dashboard/templates/index.html`
- **New sensors** — Add readers in `src/capture/`, wire into `main.py` scheduler
- **Model upgrades** — Drop a new `.tflite` in `models/`, update config
- **Prompt tuning** — Edit `src/social/templates.py` for different post styles
