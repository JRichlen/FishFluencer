# FishFluencer — Build & Design Artifacts

Companion to [`ARCHITECTURE.md`](../ARCHITECTURE.md). The root doc covers
software architecture; the files here cover the **physical build** and
**runtime data flow**, so you can take the hardware out of the box and end
up with a Coral Dev Board posting on behalf of a fish (or a dog — see
[`modes.md`](modes.md)).

## Hardware build

| Doc | What it covers |
|---|---|
| [`hardware/wiring.md`](hardware/wiring.md) | Pinout, DS18B20 1-Wire wiring with pull-up, USB/HDMI/power cabling, full connection table |
| [`hardware/assembly.md`](hardware/assembly.md) | Step-by-step physical build: enclosure, camera mount, probe placement, cable routing, safety notes |
| [`hardware/bringup.md`](hardware/bringup.md) | First-boot: Mendel flash, 1-Wire enable, camera enum, Edge TPU smoke test, GitHub deploy key, end-to-end check |
| [`hardware/dog-kennel-mounting.md`](hardware/dog-kennel-mounting.md) | Dog-mode physical setup — camera placement, lighting, probe placement, dog-safety considerations |

## Runtime modes

| Doc | What it covers |
|---|---|
| [`modes.md`](modes.md) | The `fish` vs `dog` mode switch — what changes, what stays the same, when to use which |

## System diagrams

| Doc | What it covers |
|---|---|
| [`diagrams/system-architecture.md`](diagrams/system-architecture.md) | Component block diagram (Mermaid) — capture → inference → behavior → post |
| [`diagrams/posting-cycle.md`](diagrams/posting-cycle.md) | Sequence diagram of a single scheduled post (09:00 / 17:00) |
| [`diagrams/ota-error-loop.md`](diagrams/ota-error-loop.md) | OTA pull + error-report push + auto-fix PR loop |

All diagrams use Mermaid and render natively on GitHub.

## Reading order

1. **`hardware/wiring.md`** — confirm you have every cable; flag any
   missing adapters before you start building.
2. **`hardware/assembly.md`** — physical build.
3. **`hardware/bringup.md`** — first power-on through end-to-end smoke
   test.
4. **`diagrams/*`** — reference while writing/extending code.
