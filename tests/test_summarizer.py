"""Tests for src/data/summarizer.py"""

from unittest.mock import MagicMock

from data.summarizer import BehaviorSummarizer


class TestBehaviorSummarizer:
    def _make_db(self, behaviors=None, temps=None, snapshots=None):
        db = MagicMock()
        db.get_behavior_summary.return_value = behaviors or []
        db.get_recent_temps.return_value = temps or [{"readings": 0}]

        # Mock _conn for snapshot descriptions
        mock_conn = MagicMock()
        mock_rows = [{"description": d} for d in (snapshots or [])]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        db._conn.return_value = mock_conn
        return db

    def test_empty_summary(self):
        db = self._make_db()
        summarizer = BehaviorSummarizer(db, {})
        summary = summarizer.generate_summary(hours=12.0)
        assert "Fish Tank Status Report" in summary
        assert "No fish activity detected" in summary

    def test_with_temperature(self):
        temps = [{"avg_f": 75.0, "min_f": 74.0, "max_f": 76.0, "readings": 10}]
        db = self._make_db(temps=temps)
        summarizer = BehaviorSummarizer(db, {})
        summary = summarizer.generate_summary()
        assert "75.0°F" in summary
        assert "74.0" in summary
        assert "76.0" in summary

    def test_with_behaviors(self):
        behaviors = [{
            "fish_label": "fish",
            "behavior": "cruising",
            "zone": "midwater",
            "description": "fish is cruising",
            "event_count": 5,
            "avg_confidence": 0.85,
        }]
        db = self._make_db(behaviors=behaviors)
        profiles = {"fish": {"name": "Jordan", "personality": "chill"}}
        summarizer = BehaviorSummarizer(db, profiles)
        summary = summarizer.generate_summary()
        assert "Jordan" in summary
        assert "chill" in summary
        assert "cruising" in summary

    def test_with_behaviors_no_profile(self):
        behaviors = [{
            "fish_label": "betta",
            "behavior": "resting",
            "zone": "bottom",
            "description": "resting on the bottom",
            "event_count": 3,
            "avg_confidence": 0.9,
        }]
        db = self._make_db(behaviors=behaviors)
        summarizer = BehaviorSummarizer(db, {})
        summary = summarizer.generate_summary()
        assert "Betta" in summary  # Title-cased fallback
        assert "mysterious" in summary

    def test_with_snapshot_descriptions(self):
        db = self._make_db(snapshots=["A fish near the filter", "Empty tank"])
        summarizer = BehaviorSummarizer(db, {})
        summary = summarizer.generate_summary()
        assert "Scene Descriptions" in summary
        assert "A fish near the filter" in summary

    def test_reporting_window(self):
        db = self._make_db()
        summarizer = BehaviorSummarizer(db, {})
        summary = summarizer.generate_summary(hours=6.0)
        assert "last 6 hours" in summary
