"""
Generates text-only summaries from behavior logs and sensor data.

THIS IS THE PRIVACY BOUNDARY. Only text leaves the device — never images.
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


class BehaviorSummarizer:
    """Build the text summary sent to Claude.

    Args:
        db: a FishDB.
        profiles: mapping of detection label → persona dict
            (``name``/``species``/``personality``/``quirks``).
        mode: ``"fish"`` or ``"dog"`` — selects the vocabulary used
            for the title, activity header, and temperature label.
    """

    def __init__(self, db, profiles: dict, mode: str = "fish"):
        if mode not in _MODE_VOCAB:
            raise ValueError(
                f"Unknown mode {mode!r}. Must be one of {list(_MODE_VOCAB)}."
            )
        self.db = db
        self.profiles = profiles
        self.mode = mode
        self._vocab = _MODE_VOCAB[mode]

    def generate_summary(self, hours: float = 12.0) -> str:
        behaviors = self.db.get_behavior_summary(hours=hours)
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

        if not behaviors:
            lines.append(vocab["empty_phrase"])
        else:
            lines.append(f"=== {vocab['activity_header']} ===")
            for b in behaviors:
                label = b["subject_label"]
                profile = self.profiles.get(label, {})
                name = profile.get("name", label.title())
                personality = profile.get("personality", "mysterious")

                lines.append(
                    f"\n{name} (a {personality} {label}):"
                    f"\n  - Primary behavior: {b['behavior']} "
                    f"(observed {b['event_count']}x, "
                    f"avg confidence: {b['avg_confidence']:.0%})"
                    f"\n  - Zone: {b['zone']}"
                    f"\n  - Detail: {b['description']}"
                )

        snap_descriptions = self._get_snapshot_descriptions(hours)
        if snap_descriptions:
            lines.append("\n=== Scene Descriptions (from local images) ===")
            for desc in snap_descriptions:
                lines.append(f"  - {desc}")

        return "\n".join(lines)

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
