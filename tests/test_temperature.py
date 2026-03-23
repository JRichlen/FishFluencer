"""Tests for src/capture/temperature.py"""

from pathlib import Path
from unittest.mock import patch

import pytest

from capture.temperature import DS18B20, W1_DEVICES_PATH, TempReading


class TestTempReading:
    def test_dataclass_fields(self):
        reading = TempReading(celsius=23.5, fahrenheit=74.3, timestamp=1.0, sensor_id="28-abc")
        assert reading.celsius == 23.5
        assert reading.fahrenheit == 74.3
        assert reading.timestamp == 1.0
        assert reading.sensor_id == "28-abc"


class TestDS18B20:
    def test_init_with_sensor_id(self):
        sensor_id = "28-0123456789ab"
        with patch.object(Path, "exists", return_value=True):
            # Mock the parent.name property
            sensor = DS18B20.__new__(DS18B20)
            sensor.sensor_path = W1_DEVICES_PATH / sensor_id / "w1_slave"
            sensor.sensor_id = sensor.sensor_path.parent.name
            assert sensor.sensor_id == sensor_id

    def test_auto_detect_no_sensors(self, tmp_path):
        with patch("capture.temperature.W1_DEVICES_PATH", tmp_path):
            with pytest.raises(FileNotFoundError, match="No DS18B20 found"):
                DS18B20()

    def test_auto_detect_finds_sensor(self, tmp_path):
        sensor_dir = tmp_path / "28-0123456789ab"
        sensor_dir.mkdir()
        (sensor_dir / "w1_slave").write_text("test")

        with patch("capture.temperature.W1_DEVICES_PATH", tmp_path):
            sensor = DS18B20()
            assert sensor.sensor_id == "28-0123456789ab"

    def test_read_success(self, tmp_path):
        sensor_dir = tmp_path / "28-abc"
        sensor_dir.mkdir()
        sensor_file = sensor_dir / "w1_slave"
        sensor_file.write_text(
            "73 01 4b 46 7f ff 0d 10 41 : crc=41 YES\n"
            "73 01 4b 46 7f ff 0d 10 41 t=23187\n"
        )

        with patch("capture.temperature.W1_DEVICES_PATH", tmp_path):
            sensor = DS18B20("28-abc")
            reading = sensor.read()

        assert reading.celsius == 23.19
        assert reading.fahrenheit == 73.74
        assert reading.sensor_id == "28-abc"
        assert isinstance(reading.timestamp, float)

    def test_read_crc_failure(self, tmp_path):
        sensor_dir = tmp_path / "28-abc"
        sensor_dir.mkdir()
        sensor_file = sensor_dir / "w1_slave"
        sensor_file.write_text(
            "73 01 4b 46 7f ff 0d 10 41 : crc=41 NO\n"
            "73 01 4b 46 7f ff 0d 10 41 t=23187\n"
        )

        with patch("capture.temperature.W1_DEVICES_PATH", tmp_path):
            sensor = DS18B20("28-abc")
            with pytest.raises(IOError, match="CRC check failed"):
                sensor.read()
