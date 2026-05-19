# Subject Modes — `fish` and `dog`

FishFluencer started as a fish-only system and grew dual-mode in PR #3
once it became clear the architecture was 80% subject-agnostic. The
runtime now supports two modes selected by a single config field:

```yaml
# config/default.yaml
mode: "fish"   # or "dog"
```

This page documents what differs between the two modes and what stays
the same.

---

## What the mode setting actually changes

| Component | Fish mode | Dog mode |
|---|---|---|
| Persona profiles file | `config/fish_profiles.yaml` | `config/dog_profiles.yaml` |
| Behavior vocabulary | `glass_surfing`, `surface_breathing`, `darting`, `resting`, `cruising` | `pacing`, `darting`, `resting`, `cruising` (no surface-breathing) |
| Zone labels | `surface` / `midwater` / `bottom` | `upper` / `middle` / `floor` |
| Container noun in descriptions | "tank" | "kennel" |
| Movement verbs | "dart", "cruise", "rest" | "run", "wander", "lie still" |
| Wall-pacing label | `glass_surfing` (curiosity / boredom) | `pacing` (recognized stress indicator) |
| Summary title | "Fish Tank Status Report" | "Kennel Status Report" |
| Temperature label | "Water temperature" | "Ambient temperature" |
| Claude system preamble | Fish-themed (tank life, water changes, the giant who feeds them) | Dog-themed (the great outside, the squirrel, the food bowl that fills mysteriously) |
| Stress-signal handling in prompt | n/a | Explicit instruction: do NOT make light of pacing — note it sincerely in the dog's voice |
| User-turn noun | "fish tank activity summary" | "kennel activity summary" |

## What stays the same regardless of mode

- The whole capture pipeline (camera, V4L2, Syntech adapter)
- The whole inference pipeline (Edge TPU, model file, label resolution)
- The whole tracker (centroid + distance matching)
- DS18B20 temperature reading (just labeled differently)
- DB schema (`subject_id` / `subject_label` columns are mode-neutral)
- Image lifecycle (snapshot capture, description, auto-purge after 24h)
- OTA sync, error reporting, error-report redaction
- Dashboard (URL, layout, API endpoints)
- Privacy boundary: no images leave the device in either mode
- Systemd unit names, CLI signature, env vars

## The detection-label whitelist

The Coral COCO base model emits 80 classes — `fish`, `dog`, `cat`,
`person`, and many more. In a real kennel, the camera may catch a
cat on the windowsill or a person walking past. To keep dog-mode
posts focused on the dog, set `subject_classes` in `config/default.yaml`:

```yaml
mode: "dog"
subject_classes: ["dog"]    # ignore everything else
```

Fish-mode equivalent:

```yaml
mode: "fish"
subject_classes: ["fish", "betta", "goldfish", "tetra"]
```

Empty list (default) accepts every detection — useful while bringing
up the system or running on a fine-tuned single-class model.

## Switching modes on a live device

Edit `config/default.yaml`, change `mode`, and restart:

```bash
sudo systemctl restart fishfluencer
```

The database doesn't need to change — old rows keep their original
behavior strings (`glass_surfing`) but new ones in dog mode write
`pacing`. The summarizer joins on `subject_label`, so a query window
that spans the mode change shows both vocabularies side by side.

If you migrate from a build older than this PR, the first start in
either mode also runs the one-time column rename
(`fish_id` → `subject_id`, `fish_label` → `subject_label`).

## What dog mode is NOT (be honest about limitations)

This is **Tier 1** dog support — behavior is inferred from centroid
position and speed only. That gives you:

- "Rex is pacing at the kennel door" — yes
- "Rex is running" — yes
- "Rex is lying still" — yes
- "Rex is in the upper third of frame" — yes

It does **not** give you:

- "Rex is sleeping" vs "Rex is lying still and watchful" — requires
  pose / eye-state detection
- "Rex is panting" — requires audio
- "Rex is eating" — requires multi-object reasoning (dog + food bowl)
- Per-dog identity persistence across restarts — the tracker re-IDs
  every start; if you have two dogs, fine-tune a model with
  per-dog classes (e.g. `dog_rex`, `dog_daisy`)

For a real welfare-monitoring product you'd want Tier 2 — pose
estimation alongside object detection. See the discussion in PR #3.

## Where to mount the camera for dog mode

See [`hardware/dog-kennel-mounting.md`](hardware/dog-kennel-mounting.md).
