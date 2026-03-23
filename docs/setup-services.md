# Service Configuration

Configure systemd services, API keys, and the fish personality profile.

## Prerequisites

- [OS Setup](setup-os.md), [Python Setup](setup-python.md), and [Sensor Setup](setup-sensors.md) completed

## Steps

### 1. Set your Anthropic API key

```bash
sudo mkdir -p /etc/fishfluencer
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" | sudo tee /etc/fishfluencer/env
sudo chmod 600 /etc/fishfluencer/env
```

### 2. Place your Edge TPU model

Copy your compiled Edge TPU model and labels file:

```bash
cp /path/to/detect_fish_edgetpu.tflite /opt/fishfluencer/models/
cp /path/to/labels.txt /opt/fishfluencer/models/
```

See [models/README.md](../models/README.md) for model training instructions.

### 3. Customize fish profile

Edit `config/fish_profiles.yaml` with your fish's personality:

```yaml
fish:
  name: "Jordan"
  species: "fish"
  personality: "chill observer with a dry sense of humor"
  quirks: >
    refers to the filter as 'the spa jets', calls food time
    'the daily feast from the sky giant'
```

### 4. Register systemd services

```bash
cd /opt/fishfluencer
bash scripts/register_services.sh
```

### 5. Start FishFluencer

```bash
sudo systemctl start fishfluencer
sudo systemctl start fishfluencer-sync.timer
sudo systemctl start fishfluencer-purge.timer
```

### 6. Verify operation

```bash
# Check service status
sudo systemctl status fishfluencer

# Follow live logs
journalctl -u fishfluencer -f

# Check timers
systemctl list-timers fishfluencer-*
```

## Automated Updates

The GitHub sync timer pulls code updates every 15 minutes. To update manually:

```bash
cd /opt/fishfluencer
git pull origin main
sudo systemctl restart fishfluencer
```
