"""
Generates text-only summaries from behavior logs and sensor data.

THIS IS THE PRIVACY BOUNDARY. Only text leaves the device — never images.

Tier 2: events are now emitted on transitions + every
``checkpoint_interval_seconds`` (default 60s) rather than every frame.
``BehaviorSummarizer`` uses event timestamps to approximate sustained
behavior duration ("Rex paced for 12 minutes") instead of just
counting frames.
"""

import logging
import time
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

# Per-mode wording for the summary header and the temperature line.
_MODE_VOCAB = {
    "fish": {
        "title": "Fish Tank Status Report",
        "activity_header": "Fish Activity",
        "empty_phrase": "No fish activity detected in this period.",
        "temp_label": "Water temperature",
    },
    "dog": {
        "title": "Kennel Status Report",
        "activity_header": "Kennel Activity",
        "empty_phrase": "No subject activity detected in this period.",
        "temp_label": "Ambient temperature",
    },
}


def _humanize_duration(seconds: float) -> str:
    """Render a duration in seconds as a short human-readable string."""
    if seconds < 60:
        return f"~{int(seconds)} s"
    minutes = seconds / 60
    if minutes < 60:
        return f"~{minutes:.0f} min"
    hours = minutes / 60
    return f"~{hours:.1f} h"


class BehaviorSummarizer:
    """Build the text summary sent to Claude.

    Args:
        db: a FishDB.
        profiles: mapping of detection label → persona dict
            (``name``/``species``/``personality``/``quirks``).
        mode: ``"fish"`` or ``"dog"`` — selects the vocabulary used
            for the title, activity header, and temperature label.
        checkpoint_interval_seconds: matches the analyzer's setting;
            used to estimate the duration of the most recent span
            (the trailing checkpoint event was emitted up to this far
            ago, so we add it back when computing duration).
    """

    def __init__(
        self,
        db,
        profiles: dict,
        mode: str = "fish",
        checkpoint_interval_seconds: float = 60.0,
    ):
        if mode not in _MODE_VOCAB:
            raise ValueError(
                f"Unknown mode {mode!r}. Must be one of {list(_MODE_VOCAB)}."
            )
        self.db = db
        self.profiles = profiles
        self.mode = mode
        self.checkpoint_interval = checkpoint_interval_seconds
        self._vocab = _MODE_VOCAB[mode]

    def generate_summary(self, hours: float = 12.0) -> str:
        spans = self.db.get_behavior_spans(hours=hours)
        temps = self.db.get_recent_temps(hours=hours)
        now = datetime.now()
        vocab = self._vocab

        lines = [
            f"=== {vocab['title']} ===",
            f"Generated: {now.strftime('%A, %B %d at %I:%M %p')}",
            f"Reporting window: last {hours:.0f} hours",
            "",
        ]

        if temps and temps[0]["readings"]:
            t = temps[0]
            lines.append(
                f"{vocab['temp_label']}: {t['avg_f']:.1f}°F "
                f"(range: {t['min_f']:.1f}–{t['max_f']:.1f}°F)"
            )
            lines.append("")

        if not spans:
            lines.append(vocab["empty_phrase"])
        else:
            lines.append(f"=== {vocab['activity_header']} ===")
            # Group spans by subject so we can put all of a subject's
            # behaviors together in the summary.
            by_subject: dict = {}
            for s in spans:
                by_subject.setdefault(s["subject_label"], []).append(s)

            for label, subject_spans in by_subject.items():
                profile = self.profiles.get(label, {})
                name = profile.get("name", label.title())
                personality = profile.get("personality", "mysterious")

                lines.append(f"\n{name} (a {personality} {label}):")
                for s in subject_spans:
                    duration_s = self._estimate_duration(s)
                    lines.append(
                        f"  - {s['behavior']} for {_humanize_duration(duration_s)} "
                        f"(zone: {s['zone']}, "
                        f"confidence: {s['avg_confidence']:.0%})"
                        f"\n      detail: {s['description']}"
                    )

        snap_descriptions = self._get_snapshot_descriptions(hours)
        if snap_descriptions:
            lines.append("\n=== Scene Descriptions (from local images) ===")
            for desc in snap_descriptions:
                lines.append(f"  - {desc}")

        return "\n".join(lines)

    def _estimate_duration(self, span: dict) -> float:
        """Approximate the wall-clock duration of a behavior span.

        Each behavior emits one event on transition plus one every
        ``checkpoint_interval`` seconds while sustained. So:
            duration ≈ (last_ts - first_ts) + checkpoint_interval
        The ``+ checkpoint_interval`` accounts for the time between
        the trailing checkpoint and the (unknown) actual end of the
        behavior — at worst the analyzer was about to emit the next
        checkpoint or transition.
        """
        first_ts = span["first_ts"]
        last_ts = span["last_ts"]
        return max(0.0, last_ts - first_ts) + self.checkpoint_interval

    def _get_snapshot_descriptions(self, hours: float) -> List[str]:
        since = time.time() - hours * 3600
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT description FROM snapshots "
                "WHERE timestamp > ? AND description IS NOT NULL "
                "ORDER BY timestamp DESC LIMIT 10",
                (since,),
            ).fetchall()
            return [r["description"] for r in rows]


class AlertSummarizer:
    """Build the focused text summary for a heat-stroke alert post.

    Heat-stroke alerts are urgent and bypass the periodic 12-hour
    summary. The output is a small text payload describing the
    current temperature, the threshold, and the dog's most recent
    behavior — enough for Claude to write a sincere alert post in
    the dog's voice.
    """

    def __init__(self, db, profiles: dict):
        self.db = db
        self.profiles = profiles

    def generate_alert_summary(self, reading, threshold_f: float) -> str:
        spans = self.db.get_behavior_spans(hours=1.0)
        now = datetime.now()

        lines = [
            "=== HEAT-STROKE ALERT ===",
            f"Generated: {now.strftime('%A, %B %d at %I:%M %p')}",
            f"Ambient temperature: {reading.fahrenheit:.1f}°F "
            f"(threshold: {threshold_f:.1f}°F)",
            "",
            "This is an urgent welfare alert, not a routine update.",
            "The post should be in the dog's voice but should make it "
            "unambiguously clear to a reader that the kennel is hot "
            "and the dog needs intervention.",
            "",
        ]

        if spans:
            lines.append("=== Most recent behavior (last hour) ===")
            for s in spans[:3]:
                label = s["subject_label"]
                profile = self.profiles.get(label, {})
                name = profile.get("name", label.title())
                lines.append(f"  - {name}: {s['behavior']} ({s['description']})")
        else:
            lines.append("No recent subject activity detected.")

        return "\n".join(lines)
