# FishFluencer — Copilot Instructions

## Project Overview

FishFluencer is a privacy-first, edge-AI fish surveillance system running on a
Google Coral Edge TPU Dev Board. The fish's name is **Jordan**.

## Architecture

- **Language:** Python 3.9+
- **Hardware:** Google Coral Dev Board (Mendel Linux)
- **ML:** TensorFlow Lite + PyCoral for Edge TPU inference
- **Database:** SQLite3 (all data stays on-device)
- **API:** Anthropic Claude (text-only — no images leave the device)
- **Config:** YAML with environment variable overrides

## Code Conventions

- Apply **DRY** and **KISS** principles
- Use `logging` module (never `print`)
- Type hints on all function signatures
- Docstrings on all public classes and functions
- Use `dataclass` for data containers
- Use `pathlib.Path` instead of string paths
- Use `contextmanager` for resource management

## Privacy Rules

- **No images ever leave the device** — only text summaries
- API keys stored in systemd environment files, never in code
- Error reports are sanitized before pushing to GitHub
- Snapshot images are auto-purged after configurable retention period

## Testing

- 100% unit test coverage required for all new code
- Tests use `pytest` with `pytest-cov`
- Mock external dependencies (camera, Edge TPU, HTTP, filesystem)
- Tests live in `tests/` directory, mirroring `src/` structure

## File Structure

```
src/capture/     — Camera and sensor input
src/inference/   — ML detection, tracking, behavior analysis
src/data/        — Database, summarizer, image lifecycle
src/social/      — Claude API, publishing, templates
src/sync/        — GitHub OTA updates, error reporting
src/utils/       — Config loading, logging
```
