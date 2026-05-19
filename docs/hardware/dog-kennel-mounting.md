# Dog Kennel Mounting Guide

Companion to [`assembly.md`](assembly.md) for the dog-mode subject.
The electrical build (Coral, DS18B20, camera, display, power) is
identical — this doc only covers what changes physically when the
subject is a dog in a kennel instead of a fish in a tank.

If you have the rig already running for a fish tank, you can switch
to dog mode by editing `config/default.yaml`, moving the camera and
probe, and restarting the service. See [`../modes.md`](../modes.md).

---

## Camera placement

The IMX291 has a roughly 90° horizontal field of view. For a typical
36"×24"×30" indoor kennel, you have three reasonable mounting points:

| Position | Pros | Cons |
|---|---|---|
| Top-center, lens pointing down | Whole-kennel coverage, no perspective foreshortening | Dog mostly seen from above — limited body-language signal |
| Front, looking through the door | Best face-on view, lets you see when the dog is at the door (a key pacing cue) | Door material may obstruct (bars OK, solid wire mesh causes glare); fixed dog distance varies a lot |
| **Front-corner at dog-eye height (recommended)** | Captures both the floor and the door area; centroid x/y maps cleanly onto frame thirds; dog occupies a meaningful portion of frame | Far corner of kennel may be in shadow |

For Tier 1 (centroid-based behaviors), the front-corner mount is the
sweet spot — `pacing` detection assumes the dog moves laterally
across the camera's field of view, which is exactly what kennel
pacing looks like from this angle.

### Frame-zone meaning

In dog mode the `BehaviorAnalyzer` splits the vertical extent of the
frame into thirds and labels them `upper` / `middle` / `floor`. For
the front-corner mount, these correspond roughly to:

- `upper` — top of kennel / standing-dog head / leaping
- `middle` — sitting dog body / wall-mid-height
- `floor` — lying-down dog / food-bowl level

If you mount overhead, the zones become front / middle / back of the
kennel from the camera's perspective. Same labels, different physical
meaning — calibrate your behavior thresholds (`darting_speed_threshold`
in particular) against what you actually see.

## Lighting

This is the biggest difference from a fish tank. Tank lighting is
constant; kennel lighting varies wildly:

- Daylight through a window — bright but moves across the day
- Room lights on — moderate, often warm-toned
- Lights off — the IMX291 is low-light optimized but still needs
  *some* light; pure darkness gives zero usable frames

For overnight monitoring, add a continuous low-level light source.
A 5 W warm LED in the room (not pointed at the kennel) is usually
enough.

If you see wildly fluctuating behavior counts at sunset/sunrise,
that's the auto-exposure adjusting and the detector confidence
dipping — not actual fluctuating behavior. Consider raising
`detector.confidence_threshold` from `0.5` to `0.6` to filter out
the noisy hours.

## DS18B20 placement in dog mode

The probe measures **ambient kennel temperature**, not water. This
is genuinely useful for heat-stroke alerting — a kennel in direct
sun can exceed 30 °C/86 °F quickly.

Mount the probe stainless tip away from the dog, away from any heat
sources, and at roughly the dog's body height. Inside a small
project box with ventilation slots, or zip-tied to a wall mount
behind a guard so the dog can't chew it. The probe's stainless
sheath is dog-tooth-resistant but the cable jacket is not.

> **Do not** mount the probe where the dog can reach the cable.
> The DS18B20 cable is sold for hobbyist use; it's not designed to
> survive determined chewing. Even a "supervised" dog will find it.

For an outdoor kennel, the existing wiring still works but cable
routing needs more thought — see [`assembly.md`](assembly.md) §6.

## Heat-stroke alerts (Tier 2)

Heat-stroke alerting is built in. Enable it in `config/default.yaml`:

```yaml
heat_stroke_alert:
  enabled: true
  threshold_f: 85.0       # tune for your dog and breed
  cooldown_minutes: 30    # don't re-alert more than once per N min
```

When the DS18B20 reads at or above `threshold_f`, the orchestrator
bypasses the periodic 12-hour summary and generates a focused
alert post **immediately**. The post goes through the same
publisher path as scheduled posts — so it lands on whatever
platforms you've configured, with whatever credentials you've set
(or via `DryRunPublisher` to the logs if you haven't).

The `cooldown_minutes` field rate-limits repeat alerts during a
sustained heat event so the social feed doesn't fill up with the
same alert every 5 minutes.

Caveats:

- **This is not a substitute for a real welfare alarm.** Twitter /
  Bluesky aren't pager-grade notifications. If a dog being too hot
  is a serious safety concern, also wire up a dedicated push
  channel (Pushover, SMS, etc.) — the framework doesn't ship with
  one but the alert hook in `src/main.py:_check_heat_stroke` is
  where you'd add it.
- The threshold default (85°F / 29°C) is conservative for most
  breeds; tune for your dog's tolerance and your local climate.
- The DS18B20 reads ambient air, not core body temperature, so a
  shaded probe and a hot dog can disagree.

## Detection-class whitelist

Kennels often have a window or a hallway in frame. People walking
past will register as COCO class `person` (0) and a roaming cat
will register as `cat` (16). To keep posts focused on the dog,
set in `config/default.yaml`:

```yaml
mode: "dog"
subject_classes: ["dog"]
```

This drops every non-dog detection at the source. If you ever want
to know who walked past — that's out of scope for FishFluencer; use
a separate motion sensor or a dedicated home-security camera.

## Bring-up checklist for dog mode

Once the rig is assembled per [`assembly.md`](assembly.md) and the
device is booted per [`bringup.md`](bringup.md):

- [ ] `mode: "dog"` set in `config/default.yaml`
- [ ] `subject_classes: ["dog"]` set (recommended)
- [ ] `primary_poster` set to a key in `config/dog_profiles.yaml`
      (default: `dog`)
- [ ] Camera mounted per the placement guidance above; framing
      shows the dog at expected resting position taking up ≥ 20% of
      frame height
- [ ] DS18B20 probe out of the dog's reach
- [ ] At least one lighting source — never pitch darkness
- [ ] Smoke-test: with the dog in the kennel, watch
      `journalctl -u fishfluencer -f` for `Behavior: ...` lines
      labeled `dog`
- [ ] After the next `post_times` tick, confirm a post appears in
      the DB (`sqlite3 data/fishfluencer.db 'select content from
      posts order by id desc limit 1;'`)
