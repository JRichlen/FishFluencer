# Python Environment Setup

Set up the Python virtual environment and install application dependencies.

## Prerequisites

- [OS Setup](setup-os.md) completed
- Python 3.9+ available (`python3 --version`)

## Steps

### 1. Clone the repository

```bash
REPO_DIR="/opt/fishfluencer"
sudo mkdir -p "$REPO_DIR"
sudo chown mendel:mendel "$REPO_DIR"
git clone https://github.com/JRichlen/FishFluencer.git "$REPO_DIR"
cd "$REPO_DIR"
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure git for error log pushing

```bash
git config user.email "fishfluencer-device@local"
git config user.name "FishFluencer Device"
```

### 5. Verify installation

```bash
python -c "import yaml, httpx, schedule; print('Dependencies OK')"
```

## Next Step

→ [Sensor Wiring & Setup](setup-sensors.md)
