#!/usr/bin/env bash
# FishFluencer — First-time device setup
# Run this on the Google Coral Dev Board after flashing Mendel Linux.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== FishFluencer Device Setup ==="
echo "Repo directory: $REPO_DIR"

# --- System packages ---
echo "[1/6] Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3-venv python3-pip \
    git \
    libopencv-dev python3-opencv \
    sqlite3 \
    v4l-utils \
    i2c-tools

# --- 1-Wire for DS18B20 ---
echo "[2/6] Enabling 1-Wire interface..."
if ! grep -q "w1-gpio" /etc/modules; then
    echo "w1-gpio" | sudo tee -a /etc/modules
    echo "w1-therm" | sudo tee -a /etc/modules
fi
sudo modprobe w1-gpio || true
sudo modprobe w1-therm || true

# --- Python virtual environment ---
echo "[3/6] Setting up Python venv..."
cd "$REPO_DIR"
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# --- PyCoral (Edge TPU runtime) ---
echo "[4/6] Installing PyCoral..."
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y libedgetpu1-std python3-pycoral

# --- Git configuration for log pushing ---
echo "[5/6] Configuring git..."
git config user.email "fishfluencer-device@local"
git config user.name "FishFluencer Device"

# --- Install systemd services ---
echo "[6/6] Installing systemd services..."
bash "$SCRIPT_DIR/register_services.sh"

# --- Environment file for API key ---
sudo mkdir -p /etc/fishfluencer
if [ ! -f /etc/fishfluencer/env ]; then
    echo "ANTHROPIC_API_KEY=your-key-here" | sudo tee /etc/fishfluencer/env > /dev/null
    sudo chmod 600 /etc/fishfluencer/env
    echo "  → Created /etc/fishfluencer/env — edit with your actual API key"
fi

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Set your API key:  sudo nano /etc/fishfluencer/env"
echo "  2. Place your Edge TPU model in models/"
echo "  3. Edit config/fish_profiles.yaml with your fish characters"
echo "  4. Start:  sudo systemctl start fishfluencer"
echo "  5. Logs:   journalctl -u fishfluencer -f"
