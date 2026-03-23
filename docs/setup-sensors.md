# Sensor Wiring & Setup

Connect the camera and temperature sensor to the Google Coral Dev Board.

## Camera — Arducam IMX291

### Parts

- Arducam 1080P IMX291 USB camera
- Syntech USB-C to USB adapter

### Wiring

1. Plug the Arducam's USB cable into the **Syntech USB-C adapter**
2. Plug the adapter into the Coral Dev Board's **USB-C port**

### Verification

```bash
# List video devices
v4l2-ctl --list-devices

# Should show /dev/video0 (or similar)
ls /dev/video*
```

## Temperature Sensor — DS18B20

### Parts

- DS18B20 waterproof temperature probe
- 4.7 kΩ resistor (pull-up)

### Wiring Diagram

```
Coral Dev Board                  DS18B20
┌─────────────┐                  ┌─────┐
│   3.3V pin  │──────┬──────────│ VCC │
│             │    [4.7kΩ]       │     │
│   GPIO 4   │──────┴──────────│ DATA│
│   GND pin  │─────────────────│ GND │
└─────────────┘                  └─────┘
```

### Verification

```bash
# Check that the sensor is detected
ls /sys/bus/w1/devices/28-*

# Read temperature (raw)
cat /sys/bus/w1/devices/28-*/w1_slave
# Expected output:
#   73 01 4b 46 7f ff 0d 10 41 : crc=41 YES
#   73 01 4b 46 7f ff 0d 10 41 t=23187
# (t=23187 means 23.187°C)
```

## Display — Hamityson 7" HDMI

1. Connect the display to the Dev Board's **Mini HDMI** port
2. Power the display via its USB cable

## Next Step

→ [Service Configuration](setup-services.md)
