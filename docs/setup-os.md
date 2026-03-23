# Operating System Setup

Prepare the Google Coral Dev Board for FishFluencer.

## Prerequisites

- Google Coral Dev Board with Mendel Linux flashed
- MicroSD card (≥32 GB) inserted
- Network connection (Ethernet or Wi-Fi)

## Steps

### 1. Flash Mendel Linux

Follow the official [Coral Getting Started Guide](https://coral.ai/docs/dev-board/get-started/) to flash Mendel Linux to the Dev Board.

### 2. Connect via serial or SSH

```bash
# Via serial (first time)
screen /dev/ttyUSB0 115200

# Via SSH (after network is configured)
ssh mendel@<board-ip>
```

### 3. Update system packages

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### 4. Install core dependencies

```bash
sudo apt-get install -y \
    python3-venv python3-pip \
    git \
    libopencv-dev python3-opencv \
    sqlite3 \
    v4l-utils \
    i2c-tools
```

### 5. Enable 1-Wire interface for temperature sensor

```bash
# Load kernel modules
sudo modprobe w1-gpio
sudo modprobe w1-therm

# Persist across reboots
echo "w1-gpio" | sudo tee -a /etc/modules
echo "w1-therm" | sudo tee -a /etc/modules
```

### 6. Install Edge TPU runtime

```bash
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y libedgetpu1-std python3-pycoral
```

## Next Step

→ [Python Environment Setup](setup-python.md)
