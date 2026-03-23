#!/usr/bin/env bash
# Register systemd services and timers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "Installing systemd services..."
sudo cp "$REPO_DIR"/systemd/*.service /etc/systemd/system/
sudo cp "$REPO_DIR"/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable fishfluencer.service
sudo systemctl enable fishfluencer-sync.timer
sudo systemctl enable fishfluencer-purge.timer

echo "systemd services registered."
