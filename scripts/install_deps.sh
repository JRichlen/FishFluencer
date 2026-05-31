#!/usr/bin/env bash
# Idempotent Python dependency install. Runs during initial setup and
# after every OTA update that changes requirements.txt.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(pwd)}"
cd "$REPO_DIR"

if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Python deps installed in $REPO_DIR/.venv"
