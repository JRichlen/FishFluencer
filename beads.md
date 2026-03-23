# FishFluencer — Beads (Spec & Feature Tracker)

Tracking specs and features using [Beads](https://github.com/steveyegge/beads).

## 🟢 Done

- **BEAD-001**: Project scaffolding — directory structure, pyproject.toml, requirements.txt
- **BEAD-002**: Camera capture module (`src/capture/camera.py`) — OpenCV frame capture
- **BEAD-003**: Temperature sensor module (`src/capture/temperature.py`) — DS18B20 1-Wire
- **BEAD-004**: Fish detector (`src/inference/detector.py`) — Edge TPU TFLite inference
- **BEAD-005**: Centroid tracker (`src/inference/tracker.py`) — Multi-object fish tracking
- **BEAD-006**: Behavior analyzer (`src/inference/behavior.py`) — Rule-based classification
- **BEAD-007**: SQLite database (`src/data/db.py`) — Schema and CRUD operations
- **BEAD-008**: Behavior summarizer (`src/data/summarizer.py`) — Privacy-boundary text generator
- **BEAD-009**: Image manager (`src/data/image_manager.py`) — Auto-purge and storage limits
- **BEAD-010**: Post generator (`src/social/post_generator.py`) — Claude API integration
- **BEAD-011**: Publisher adapters (`src/social/publisher.py`) — Platform API stubs
- **BEAD-012**: GitHub sync agent (`src/sync/github_sync.py`) — OTA updates via git pull
- **BEAD-013**: Error log pusher (`src/sync/log_pusher.py`) — Sanitized error reports
- **BEAD-014**: Config loader (`src/utils/config.py`) — YAML with env var resolution
- **BEAD-015**: Main orchestrator (`src/main.py`) — Entry point tying all subsystems
- **BEAD-016**: systemd services — Service, timer, and purge unit files
- **BEAD-017**: Setup scripts — Device bootstrap, dependency install, service registration
- **BEAD-018**: CI/CD workflows — lint-and-test.yml, auto-fix.yml
- **BEAD-019**: README with hardware setup guide
- **BEAD-020**: Software setup docs split into sub-procedures (docs/*.md)
- **BEAD-021**: Copilot agent instructions (.github/copilot-instructions.md)
- **BEAD-022**: Unit tests — 100% coverage for all implemented modules

## 🟡 In Progress

_(none)_

## 🔴 Backlog

- **BEAD-100**: Twitter/X API publisher implementation
- **BEAD-101**: Bluesky API publisher implementation
- **BEAD-102**: Instagram API publisher implementation
- **BEAD-103**: Mastodon API publisher implementation
- **BEAD-104**: HDMI dashboard (Flask/PyGame) implementation
- **BEAD-105**: Edge TPU model training pipeline and documentation
- **BEAD-106**: DeepSORT upgrade for tracker (re-identification after occlusion)
- **BEAD-107**: ML-based behavior classification head (replace rule-based)
- **BEAD-108**: Multi-fish personality profiles and rotation
