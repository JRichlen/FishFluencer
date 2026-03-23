#!/usr/bin/env bash
# Install Python dependencies into the virtual environment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
