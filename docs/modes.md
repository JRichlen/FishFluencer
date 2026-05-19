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

## Tier 2 features (current)

| Feature | Where it lives |
|---|---|
| Posture classification (`LYING_DOWN` / `SITTING` / `STANDING`) for dog mode | `src/inference/behavior.py` — `_classify` posture branch, gated by bbox aspect ratio thresholds |
| Span-based event emission (one event per behavior transition + one checkpoint every 60s, instead of one per frame) | `src/inference/behavior.py` — `BehaviorAnalyzer` keeps per-subject state |
| Heat-stroke alert posts | `src/main.py` — `_check_heat_stroke` / `_generate_alert_post`, gated by `heat_stroke_alert` config |
| Subject identity persistence across restarts | `src/inference/tracker.py` — `CentroidTracker.save_state` / `_load_state`, JSON state file |
| Humanized duration in summaries ("paced for ~12 min") | `src/data/summarizer.py` — `_estimate_duration` from event timestamps |

Tunable knobs in `config/default.yaml`:

```yaml
behavior:
  checkpoint_interval_seconds: 60.0   # how often a sustained behavior re-emits
  posture_aspect_lying: 1.4           # bbox W/H above which a still dog is LYING_DOWN
  posture_aspect_sitting: 0.9         # bbox W/H below which a still dog is STANDING

heat_stroke_alert:
  enabled: false
  threshold_f: 85.0
  cooldown_minutes: 30

tracker_state_path: "data/tracker_state.json"   # null to disable persistence
```

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

This is **Tier 2** dog support. We have:

- "Rex is pacing at the kennel door" (with stress-indicator phrasing
  in the prompt) — yes
- "Rex is running" — yes
- "Rex is lying down" vs "sitting" vs "standing" — yes, derived from
  bbox aspect ratio. **Requires a side-mounted camera** — a top-down
  view sees a roughly square bbox regardless of posture and degrades
  to undifferentiated `SITTING`.
- Heat-stroke alerting — yes, threshold-based, with cooldown
- Subject ID persistence across service restarts — yes, position-
  and-label-based "poor-man's re-ID" via a JSON state file
- Behavior duration in human-friendly form ("Rex lay down for
  ~25 min") — yes, derived from span emission timestamps

What it still does **not** give you:

- True dog pose estimation. We deliberately do not add a second
  Edge TPU model because there is no widely-available, Edge-TPU-
  compiled pose model trained on dogs. Human PoseNet on a dog
  produces nonsense keypoints. Aspect-ratio posture is the honest
  signal we can produce from the existing detector.
- "Rex is sleeping" vs "Rex is lying still and watchful" — requires
  eye-state / head-pose, requires pose estimation that doesn't
  exist yet for Edge TPU.
- "Rex is panting" — requires audio + a separate model.
- "Rex is eating" — requires multi-object reasoning (dog + food
  bowl); the framework supports detecting both classes, but no
  scene-relationship rules are implemented.
- Per-dog identity from appearance — the position-based rehydration
  works well for "one dog in a kennel" and degrades for "two dogs
  that rotate through the same favorite corner." For multi-dog
  reliability, fine-tune a detector with per-dog classes (e.g.
  `dog_rex`, `dog_daisy`).

For Tier 3 (real welfare monitoring), the missing pieces are a
dog-trained pose model on Edge TPU (would have to be trained and
compiled in-house), audio capture + classification (panting,
barking, whining), and per-instance appearance embeddings. None of
those are blocked by FishFluencer's architecture — they're all
additive — but they're individually substantial pieces of work.

## Where to mount the camera for dog mode

See [`hardware/dog-kennel-mounting.md`](hardware/dog-kennel-mounting.md).
