#!/usr/bin/env bash
# First-time device setup for the Coral Dev Board.
# See docs/hardware/bringup.md for the verification-heavy walkthrough.
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
    i2c-tools \
    curl

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
REPO_URL="${FISHFLUENCER_REPO_URL:-https://github.com/JRichlen/FishFluencer.git}"

if [ -d "$REPO_DIR" ]; then
    echo "Repo exists, pulling latest..."
    cd "$REPO_DIR"
    git pull origin main || true
else
    echo "Cloning repo..."
    sudo mkdir -p "$REPO_DIR"
    sudo chown "$USER:$USER" "$REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# --- Python virtual environment ---
bash scripts/install_deps.sh

# --- PyCoral (Edge TPU runtime) ---
if ! python3 -c "from pycoral.utils import edgetpu" >/dev/null 2>&1; then
  echo "Installing PyCoral..."
  echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
      sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
  sudo apt-get update
  sudo apt-get install -y libedgetpu1-std python3-pycoral
fi

# --- Git configuration for log pushing ---
echo "Configuring git for error log push..."
git config user.email "fishfluencer-device@local"
git config user.name "FishFluencer Device"

# --- Install systemd services ---
bash scripts/register_services.sh

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Set your API key:  sudo systemctl edit fishfluencer"
echo "     Add: Environment=ANTHROPIC_API_KEY=sk-ant-..."
echo "  2. Place your Edge TPU model in models/"
echo "  3. Edit config/fish_profiles.yaml with your fish characters"
echo "  4. Start:  sudo systemctl start fishfluencer"
echo "  5. Logs:   journalctl -u fishfluencer -f"
