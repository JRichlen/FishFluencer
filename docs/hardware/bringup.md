# Bring-up Checklist

First-power-on through end-to-end smoke test for FishFluencer. Run
these in order. Every step has a verification command; do not skip the
verification — silent failures here become noisy failures at 3 a.m.

Estimated time: **60–90 min** for first build.

---

## 0. Prerequisites

- Hardware fully assembled per [`assembly.md`](assembly.md).
- A laptop on the same network as the Coral, with `mdt` (Mendel
  Development Tool) installed:

  ```bash
  pip install --user mendel-development-tool
  ```

- A GitHub repo for FishFluencer (fork of this one, or your own) and
  an Anthropic API key.

---

## 1. Flash Mendel Linux

If your Coral is brand-new, the on-board eMMC ships with Mendel; you
can skip this step. To re-flash or use the microSD path:

1. Download the latest Mendel image from
   [coral.ai/software](https://coral.ai/software/).
2. Flash to microSD with `etcher` or `dd`.
3. Insert SD; boot the Coral with both USB-C cables disconnected.
4. Plug **power** into the Coral's USB-C **power** port.
5. Plug a USB-C **data** cable from your laptop into the Coral's
   USB-C **OTG** port (temporarily — the camera goes here later).

Find the device:

```bash
mdt devices                    # should list your Coral's serial
mdt shell                      # drops you into a Mendel shell
```

Set a hostname so the rest of the doc can use `fishfluencer.local`:

```bash
sudo hostnamectl set-hostname fishfluencer
```

Reboot, then disconnect the data cable from the OTG port and plug the
**Syntech adapter + camera** in instead.

---

## 2. Update & install base packages

SSH in (Mendel image enables SSH by default for the `mendel` user):

```bash
ssh mendel@fishfluencer.local       # default password: mendel — change it
passwd
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-pip v4l-utils i2c-tools \
                    libopencv-dev python3-opencv sqlite3
```

---

## 3. Networking

**Ethernet:** nothing to do — `ip a` should already show an address on
`eth0`.

**Wi-Fi:** use `nmcli`:

```bash
sudo nmcli dev wifi connect "YOUR_SSID" password "YOUR_PASSWORD"
nmcli connection show --active
```

Verify outbound connectivity:

```bash
curl -sI https://api.anthropic.com/v1/messages | head -1
curl -sI https://github.com | head -1
```

Both should return an HTTP status line.

---

## 4. Enable 1-Wire & verify DS18B20

```bash
echo "w1-gpio"  | sudo tee -a /etc/modules
echo "w1-therm" | sudo tee -a /etc/modules
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

Reboot once so the modules load cleanly at boot:

```bash
sudo reboot
```

After reboot, the probe should appear under `/sys/bus/w1/devices/`:

```bash
ls /sys/bus/w1/devices/
# Expect a directory named like 28-3c01b556xxxxx and a w1_bus_master1

cat /sys/bus/w1/devices/28-*/w1_slave
# Expect two lines ending in:
#   YES
#   t=22125            ← millidegrees Celsius (22.125 °C)
```

**Troubleshooting:**

| Symptom | Likely cause |
|---|---|
| No `28-*` device appears | Pull-up resistor missing, or DQ wired to wrong pin |
| `t=85000` | Power-on default — bus reads before sensor finishes conversion. Re-check pull-up and pin 1 (3.3 V) wiring |
| `t=-127000` | Bus fault / CRC fail — usually a loose Yellow wire or VDD swapped with DQ |
| `NO` on first line | Bad CRC — almost always a wiring issue, not a bad probe |

Note the device ID (`28-3c01b556xxxxx`) — drop it into
`config/default.yaml` under `temp_sensor_id` (or leave `null` for
auto-detect).

---

## 5. Verify the camera

```bash
v4l2-ctl --list-devices
# Expect "USB Camera" or similar, with /dev/video0 listed

v4l2-ctl -d /dev/video0 --list-formats-ext | head -40
# Confirm 1920x1080 is listed
```

Grab one frame end-to-end:

```bash
python3 - <<'PY'
import cv2
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
ok, frame = cap.read()
print("ok:", ok, "shape:", None if frame is None else frame.shape)
cap.release()
PY
```

Expect `ok: True shape: (1080, 1920, 3)`. If `ok: False`, the camera
is plugged into the **power** USB-C port instead of the **OTG** port —
swap and retry.

---

## 6. Edge TPU smoke test

Install the PyCoral runtime + libedgetpu (matches the script in
`ARCHITECTURE.md`):

```bash
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt update
sudo apt install -y libedgetpu1-std python3-pycoral
```

Run the canonical PyCoral classify example as a TPU heartbeat:

```bash
python3 - <<'PY'
from pycoral.utils import edgetpu
print("Coral devices:", edgetpu.list_edge_tpus())
PY
```

Expect at least one entry. Empty list = the libedgetpu package didn't
install or the TPU is disabled in BIOS-style settings (rare; usually
just an install issue).

---

## 7. Clone the repo & install Python deps

```bash
sudo mkdir -p /opt/fishfluencer
sudo chown mendel:mendel /opt/fishfluencer
git clone https://github.com/YOUR_USER/fishfluencer.git /opt/fishfluencer
cd /opt/fishfluencer

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 8. GitHub deploy key (for OTA pull + error report push)

The device pushes branches named `error-report/*` and pulls from
`main`. Generate a key on the device:

```bash
ssh-keygen -t ed25519 -C "fishfluencer-device" -f ~/.ssh/fishfluencer -N ""
cat ~/.ssh/fishfluencer.pub
```

Add the public key to your GitHub repo under **Settings → Deploy keys**
with **Allow write access** checked.

Switch the repo remote to SSH:

```bash
cd /opt/fishfluencer
git remote set-url origin git@github.com:YOUR_USER/fishfluencer.git

cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/fishfluencer
  IdentitiesOnly yes
EOF

ssh -T git@github.com    # expect: "Hi YOUR_USER/fishfluencer! ..."
```

Configure the local git identity so error-report commits are
attributable:

```bash
git config user.email "fishfluencer-device@local"
git config user.name "FishFluencer Device"
```

---

## 9. Anthropic API key

```bash
sudo systemctl edit fishfluencer    # creates an override file
```

Paste:

```ini
[Service]
Environment=ANTHROPIC_API_KEY=sk-ant-...
```

Save & exit, then:

```bash
sudo systemctl daemon-reload
```

**Never** commit the key to the repo. The repo writes only sanitized
text — see `ARCHITECTURE.md` § Privacy Architecture Summary.

---

## 10. Edge TPU model

Drop your compiled fish detection model into `models/`:

```
models/
├── detect_fish_edgetpu.tflite
└── labels.txt
```

If you don't have a custom model yet, the canonical
`ssd_mobilenet_v2_coco_quant_edgetpu.tflite` from coral.ai works for
the smoke test — it just labels every fish as `"person"` (or whatever
the closest COCO class is). Replace it before going live.

---

## 11. Smoke-test end-to-end

```bash
cd /opt/fishfluencer
source .venv/bin/activate
ANTHROPIC_API_KEY=sk-ant-... python3 -m src.main config/default.yaml
```

Watch for, in order:

1. `Camera warmup (2.0s)...` then `Camera ready.`
2. `Temp: 22.1°F` (or whatever your tank is)
3. Periodic detection log lines.
4. At the next scheduled `post_times`, `Summary generated (N chars)`
   and a `[twitter] Post: ...` line.

If all four show, kill it with Ctrl-C — the smoke test passed.

---

## 12. Install as a service

```bash
cd /opt/fishfluencer
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fishfluencer.service
sudo systemctl enable --now fishfluencer-sync.timer
sudo systemctl enable --now fishfluencer-purge.timer
```

Verify:

```bash
systemctl status fishfluencer
journalctl -u fishfluencer -f          # live logs
systemctl list-timers | grep fishfluencer
```

---

## 13. Sign-off checklist

The build is done when **all** of these are true:

- [ ] `/sys/bus/w1/devices/28-*` exists and `w1_slave` returns a real
      temperature.
- [ ] `v4l2-ctl --list-devices` shows the IMX291 and a Python OpenCV
      frame grab succeeds.
- [ ] `pycoral.utils.edgetpu.list_edge_tpus()` returns a non-empty
      list.
- [ ] `ssh -T git@github.com` succeeds with the deploy key.
- [ ] `systemctl status fishfluencer` reports `active (running)` for
      ≥ 10 minutes with no restarts.
- [ ] At the next scheduled `post_time`, a post appears in the DB
      (`sqlite3 data/fishfluencer.db 'select created_at, platform,
      substr(content,1,80) from posts order by id desc limit 5;'`).
- [ ] HDMI dashboard renders on the 7" display.

When all boxes are ticked, the rig is operational.
