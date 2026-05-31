# FishFluencer

Privacy-first edge-AI fish surveillance + cheeky social-media ghostwriter
for your aquarium. Runs on a Google Coral Dev Board: detects and tracks
fish on-device with a TensorFlow Lite Edge TPU model, classifies their
behavior, and twice a day asks Claude to write a first-person social
media post from the fish's point of view.

**No images ever leave the device.** Only text summaries are sent to the
Claude API. Photos are auto-purged after 24 hours.

## Documentation

| Doc | What it covers |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Full system architecture and module-by-module design |
| [`docs/README.md`](docs/README.md) | Index of build artifacts |
| [`docs/hardware/wiring.md`](docs/hardware/wiring.md) | Coral pinout, DS18B20 1-Wire, USB/HDMI/power cabling, part checklist |
| [`docs/hardware/assembly.md`](docs/hardware/assembly.md) | Physical build — bench setup → enclosure → cable routing |
| [`docs/hardware/bringup.md`](docs/hardware/bringup.md) | First-boot runbook with verification commands and sign-off checklist |
| [`docs/diagrams/`](docs/diagrams/) | Mermaid system + sequence diagrams |

## Quick start (on a Coral Dev Board)

```bash
# Clone, install, register systemd units
git clone https://github.com/JRichlen/FishFluencer.git /opt/fishfluencer
cd /opt/fishfluencer
bash scripts/setup.sh

# Add your Anthropic API key
sudo systemctl edit fishfluencer
# Then add: Environment=ANTHROPIC_API_KEY=sk-ant-...

# Drop your Edge TPU model into models/detect_fish_edgetpu.tflite

sudo systemctl start fishfluencer
journalctl -u fishfluencer -f
```

See [`docs/hardware/bringup.md`](docs/hardware/bringup.md) for the
verification-heavy walkthrough.

## Dev / non-Coral machine

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # runs the offline unit tests
python -m src.main config/default.yaml   # runs without camera/Coral
```

The detector and DS18B20 sensor degrade gracefully when missing — the
orchestrator logs a warning and the scheduler still runs.

## License

MIT — see [`LICENSE`](LICENSE).
