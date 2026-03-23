# 🐟 FishFluencer — AI Fish Monitor & Social Media Poster

A privacy-first, edge-AI fish surveillance system running on a **Google Coral Edge TPU Dev Board**. The system uses on-device TensorFlow Lite models to detect, classify, and track fish behavior in real time, then generates text-only behavioral summaries sent to the Claude API to craft social media posts — as if written by the fish.

**Meet Jordan** — the fish behind the posts.

> **No images ever leave the device.** Photos are used locally for inference and display, described in text, then auto-purged on a configurable schedule.

---

## Hardware Bill of Materials

| Component | Role | Interface |
|---|---|---|
| [Google Coral Dev Board](https://coral.ai/products/dev-board/) | Main compute + Edge TPU inference | — |
| [Arducam 1080P IMX291](https://www.arducam.com/) | Camera capture (low-light optimized) | USB via Syntech adapter |
| [DS18B20 Temperature Sensor](https://www.adafruit.com/product/381) | Water temperature monitoring | GPIO pin 4 (1-Wire) |
| [Hamityson 7" Mini HDMI Display](https://www.amazon.com/) | Local dashboard / status UI | Mini HDMI |
| [Syntech USB-C to USB Adapter](https://www.amazon.com/) | Camera → Dev Board connection | USB-C port |
| MicroSD Card (≥32 GB) | OS + application storage | MicroSD slot |
| 4.7 kΩ Resistor | Pull-up for DS18B20 DATA line | Inline with GPIO 4 |

---

## Hardware Setup

### Wiring Diagram

```
Google Coral Dev Board
┌──────────────────────────────────────────┐
│                                          │
│  USB-C ← Syntech Adapter ← Arducam      │
│                                          │
│  Mini HDMI ← Hamityson 7" Display        │
│                                          │
│  GPIO 4 ──┬── DS18B20 DATA              │
│           [4.7kΩ]                        │
│  3.3V  ───┘    DS18B20 VCC              │
│  GND  ──────── DS18B20 GND              │
│                                          │
│  MicroSD ← ≥32GB card (Mendel Linux)    │
└──────────────────────────────────────────┘
```

### Assembly Steps

1. **Flash Mendel Linux** onto the MicroSD card and insert it into the Coral Dev Board
2. **Connect the camera**: Plug the Arducam IMX291 USB cable into the Syntech USB-C adapter, then plug the adapter into the Dev Board's USB-C port
3. **Wire the temperature sensor**: Connect the DS18B20 to GPIO pin 4 with a 4.7 kΩ pull-up resistor between VCC (3.3V) and DATA (see wiring diagram above)
4. **Connect the display**: Plug the Hamityson 7" display into the Mini HDMI port and power it via USB
5. **Connect to network**: Use Ethernet or configure Wi-Fi for internet access

---

## Software Setup

Setup is broken into sub-procedures. Follow each in order:

1. **[Operating System Setup](docs/setup-os.md)** — Flash Mendel Linux, install system packages, enable 1-Wire, install Edge TPU runtime
2. **[Python Environment Setup](docs/setup-python.md)** — Clone repo, create venv, install dependencies
3. **[Sensor Wiring & Setup](docs/setup-sensors.md)** — Verify camera and temperature sensor connections
4. **[Service Configuration](docs/setup-services.md)** — Set API key, configure fish profile, register systemd services, start the application

### Quick Start (automated)

If you prefer a single-command setup after hardware assembly:

```bash
git clone https://github.com/JRichlen/FishFluencer.git /opt/fishfluencer
cd /opt/fishfluencer
bash scripts/setup.sh
```

Then set your API key and start:

```bash
sudo nano /etc/fishfluencer/env   # Set ANTHROPIC_API_KEY
sudo systemctl start fishfluencer
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORAL DEV BOARD (ON-DEVICE)                  │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐     │
│  │ Arducam  │───▶│ Frame Capture│───▶│ Edge TPU Inference│     │
│  │ IMX291   │    │ (OpenCV)     │    │ (TFLite + Coral)  │     │
│  └──────────┘    └──────────────┘    └────────┬──────────┘     │
│                                               │                 │
│  ┌──────────┐    ┌──────────────┐    ┌────────▼──────────┐     │
│  │ DS18B20  │───▶│ Temp Reader  │───▶│ Behavior Tracker  │     │
│  │ Sensor   │    │ (1-Wire)     │    │ (SQLite + Logic)  │     │
│  └──────────┘    └──────────────┘    └────────┬──────────┘     │
│                                               │                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Orchestrator (cron)                      │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Text Summary │  │ Claude API   │  │ Post Publisher │  │  │
│  │  │ Generator    │─▶│ (text only!) │─▶│ (API calls)    │  │  │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Local HDMI   │  │ Image Purge  │  │ GitHub Sync Agent  │   │
│  │ Dashboard    │  │ (cron)       │  │ (pull + log push)  │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Privacy Architecture

| Data Type | Stays On-Device | Leaves Device (Text Only) |
|---|---|---|
| Raw camera frames | ✅ Processed in RAM | ❌ Never |
| Saved JPEG snapshots | ✅ Auto-purged after 24h | ❌ Never |
| Fish detection boxes | ✅ Stored in SQLite | ❌ Never |
| Behavior descriptions | ✅ Stored in SQLite | ✅ As text summary to Claude API |
| Temperature readings | ✅ Stored in SQLite | ✅ As text in summary |
| Social media posts | ✅ Logged in SQLite | ✅ Published to platforms |
| Error tracebacks | ✅ Logged locally | ✅ Sanitized JSON to GitHub |
| API keys / secrets | ✅ In systemd env only | ❌ Never in repo or logs |

---

## Development

### Run tests

```bash
pip install -e ".[dev]"
pytest tests/ --cov=src --cov-report=term-missing
```

### Lint

```bash
ruff check src/ tests/
```

### Project structure

```
src/
├── capture/        Camera and sensor input
├── inference/      ML detection, tracking, behavior analysis
├── data/           Database, summarizer, image lifecycle
├── social/         Claude API, publishing, templates
├── sync/           GitHub OTA updates, error reporting
├── utils/          Config loading, logging
└── main.py         Entry point
```

---

## Spec Tracking

Features and specs are tracked in [beads.md](beads.md) using the [Beads](https://github.com/steveyegge/beads) system.

---

## License

MIT