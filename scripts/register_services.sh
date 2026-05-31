#!/usr/bin/env bash
# Register the FishFluencer systemd units. Idempotent — re-run after
# editing any *.service / *.timer file.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(pwd)}"
cd "$REPO_DIR"

sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fishfluencer.service
sudo systemctl enable fishfluencer-sync.timer
sudo systemctl enable fishfluencer-purge.timer

echo "systemd units installed and enabled."
echo "Start with:  sudo systemctl start fishfluencer"
