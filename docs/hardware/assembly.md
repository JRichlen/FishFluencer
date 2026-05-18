# Physical Assembly Guide

Step-by-step build for the FishFluencer rig. Assumes you have completed
the cable / part checklist in [`wiring.md`](wiring.md) §7.

Estimated time: **45–90 min** for first build.

---

## Bench setup

Before powering anything on:

1. Static-safe surface (anti-static mat or unplugged metal desk).
2. **Do not** put the Coral on bare metal — the underside has exposed
   pads. Use the supplied standoffs or a plastic mat.
3. Keep liquids well away from the bench. The DS18B20 probe is
   waterproof; nothing else is.

---

## Step 1 — Prepare the Coral Dev Board

1. Snap the heatsink-fan assembly onto the SoM if not already attached.
2. Insert the **flashed** microSD card (see `bringup.md` §1 to flash
   Mendel first).
3. Leave both USB-C ports unconnected for now.

---

## Step 2 — Wire the DS18B20

You can use a small breadboard for the first build and migrate to a
soldered/heat-shrunk harness once the rest works.

1. Place the **4.7 kΩ resistor** between the **3.3 V rail** and the
   **DQ rail** (this is the mandatory 1-Wire pull-up — see
   `wiring.md` §3).
2. Connect probe **Red → header pin 1** (3.3 V).
3. Connect probe **Black → header pin 6** (GND).
4. Connect probe **Yellow → header pin 7** (1-Wire data, same rail as
   the pull-up).
5. Tug-test each connection. A wire that pops out mid-assembly is the
   #1 cause of `-127 °C` readings later.

```
       3.3V ──┬───────── VDD (red)
              │
              ├── 4.7kΩ
              │
   GPIO/1W ───┴───────── DQ  (yellow)
       GND ──────────── GND (black)
```

> **Routing tip:** loop the probe cable once inside the enclosure and
> zip-tie it to a fixed point. That way an accidental tug on the
> in-tank end pulls the strain-relief loop instead of the header pins.

---

## Step 3 — Camera mount

1. Attach the Arducam to a suction-cup mount or a small bracket aimed
   at the most active part of the tank (usually the front-centre,
   slightly above mid-water).
2. Aim slightly **downward** — fish spend most time in the lower 2/3
   of the column, and downward framing minimises the surface-glare
   from the tank light.
3. Plug the camera into the **Syntech USB-C ↔ USB-A adapter**, then
   into the Coral's **USB-C OTG port** (the one **not** marked
   "power").
4. Leave 10–15 cm of cable slack at the tank — fish-tank lids are
   removed for cleaning, and you do not want to unplug the camera
   every time.

> **Glare check:** a polarising film on the front of the tank, or a
> matte hood above the camera, makes a huge difference for the
> detector. Worth doing before training a custom model on tank
> footage.

---

## Step 4 — Probe placement in the tank

1. Route the DS18B20 cable through a **cable gland**, **grommet**, or
   a notched corner of the tank lid. Sharp glass edges + 3 m of cable
   = eventual short.
2. Submerge the stainless tip **at least 3 cm** below the surface,
   away from the heater (you want average water temp, not "0.5 cm
   from the heating element" temp).
3. Use a suction cup or silicone aquarium-safe sealant to fix the
   probe tip to the back glass.
4. **Do not** submerge the cable's heat-shrink boundary. Only the
   stainless tip is rated for continuous immersion.

---

## Step 5 — Display

1. Connect HDMI between the Coral and the 7" display using the cable
   confirmed in [`wiring.md`](wiring.md) §5.
2. Connect the display's **own** 5 V supply (USB-A or barrel jack).
   Do not back-feed it from the Coral.
3. Position the display where it can be seen but is not exposed to
   tank splash. The dashboard is a local read-only view; you can also
   remote-view it via `journalctl` if you'd rather skip the display.

---

## Step 6 — Enclosure & cable routing

A simple ventilated project box keeps the Coral safe from splash and
dust. Mounting checklist:

- [ ] Coral fan intake unobstructed (≥ 1 cm clearance).
- [ ] DS18B20 cable enters via a gland or grommet — strain-relieved
      inside.
- [ ] Camera USB cable enters via a separate gland — kept away from
      the probe cable to avoid noise on the 1-Wire bus.
- [ ] HDMI exits via a notch on the opposite side from USB.
- [ ] Power cables enter together at the bottom; PSU bricks are
      **outside** the enclosure.
- [ ] No cable crosses the fan exhaust.

---

## Step 7 — Network

- **Ethernet** (preferred): plug straight into the Coral's RJ45.
- **Wi-Fi**: configured during `bringup.md` §3.

Either way, the device needs outbound HTTPS to:

- `api.anthropic.com` (post generation)
- `github.com` / `api.github.com` (OTA pull + error report push)
- Whatever social platform you publish to

Inbound access is **not** required — no SSH, no port forwarding, no
VPN.

---

## Step 8 — Pre-power inspection

Before plugging in the PSU, sanity-check:

- [ ] No bare wire touching the Coral PCB.
- [ ] DS18B20 pull-up resistor present and on the correct rails.
- [ ] Probe Red/Yellow/Black not swapped.
- [ ] Camera plugged into OTG port, **not** the power port.
- [ ] microSD card seated.
- [ ] HDMI cable seated.
- [ ] Display has its own power source.

If all green, proceed to [`bringup.md`](bringup.md) for first boot.

---

## Safety notes

- **Water and mains do not mix.** Use a GFCI/RCD outlet for the tank
  side of the build. If the probe's heat-shrink boundary ever submerges,
  pull power before retrieving.
- **The Edge TPU runs hot.** ~80 °C surface temperature under sustained
  inference is normal; don't enclose without ventilation.
- **The PSU brick is the single point of failure.** A cheap 5 V supply
  with high ripple will cause random reboots that look exactly like a
  software bug. Use a known-good supply from the start.
