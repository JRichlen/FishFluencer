"""
DS18B20 1-Wire temperature sensor reader.

Wiring on Coral Dev Board:
  - VCC  → 3.3V pin
  - GND  → GND pin
  - DATA → GPIO pin 4 (with 4.7kΩ pull-up to 3.3V)

Prerequisites (run once):
  sudo modprobe w1-gpio
  sudo modprobe w1-therm
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

W1_DEVICES_PATH = Path("/sys/bus/w1/devices")


@dataclass
class TempReading:
    celsius: float
    fahrenheit: float
    timestamp: float
    sensor_id: str


class DS18B20:
    def __init__(self, sensor_id: Optional[str] = None):
        """
        Initialize with a specific sensor ID, or auto-detect the first one.
        Sensor IDs look like '28-xxxxxxxxxxxx'.
        """
        if sensor_id:
            self.sensor_path = W1_DEVICES_PATH / sensor_id / "w1_slave"
        else:
            self.sensor_path = self._auto_detect()

        self.sensor_id = self.sensor_path.parent.name
        logger.info("DS18B20 initialized: %s", self.sensor_id)

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

        if not lines[0].strip().endswith("YES"):
            raise IOError(f"CRC check failed for sensor {self.sensor_id}")

        temp_str = lines[1].split("t=")[1]
        celsius = int(temp_str) / 1000.0
        fahrenheit = celsius * 9.0 / 5.0 + 32.0

        return TempReading(
            celsius=round(celsius, 2),
            fahrenheit=round(fahrenheit, 2),
            timestamp=time.time(),
            sensor_id=self.sensor_id,
        )
