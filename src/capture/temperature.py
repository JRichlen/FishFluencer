"""
DS18B20 1-Wire temperature sensor reader.

Wiring on Coral Dev Board (40-pin header):
  - VDD  → pin 1 (3.3 V)
  - GND  → pin 6 (GND)
  - DATA → pin 7 (1-Wire) with 4.7 kΩ pull-up to 3.3 V

Prerequisites (run once):
  sudo modprobe w1-gpio
  sudo modprobe w1-therm
  # Or persist via /etc/modules (see docs/hardware/bringup.md)
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
        if sensor_id:
            self.sensor_path = W1_DEVICES_PATH / sensor_id / "w1_slave"
        else:
            self.sensor_path = self._auto_detect()

        self.sensor_id = self.sensor_path.parent.name
        logger.info("DS18B20 initialized: %s", self.sensor_id)

    def _auto_detect(self) -> Path:
        candidates = list(W1_DEVICES_PATH.glob("28-*/w1_slave"))
        if not candidates:
            raise FileNotFoundError(
                "No DS18B20 found. Check wiring and ensure w1-gpio module is loaded."
            )
        return candidates[0]

    def read(self) -> TempReading:
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
