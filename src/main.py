"""
FishFluencer main entry point.

Ties together camera capture, Edge TPU inference, fish tracking,
behavior analysis, temperature monitoring, text summary generation,
Claude API post generation, image lifecycle, error reporting, and
the local HDMI dashboard.

Run via systemd:
    python -m src.main config/default.yaml
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path

import schedule

from src.capture.camera import FishCamera
from src.capture.temperature import DS18B20
from src.data.db import FishDB
from src.data.image_manager import ImageManager
from src.data.summarizer import AlertSummarizer, BehaviorSummarizer
from src.display.dashboard import Dashboard
from src.inference.behavior import BehaviorAnalyzer
from src.inference.detector import FishDetector
from src.inference.tracker import CentroidTracker
from src.social.post_generator import PostGenerator
from src.social.publisher import make_publisher
from src.sync.log_pusher import ErrorLogPusher
from src.utils.config import load_config, load_fish_profiles
from src.utils.logging import configure_logging

logger = logging.getLogger("fishfluencer")


class FishFluencer:
    def __init__(self, config_path: str = "config/default.yaml"):
        self.config = load_config(config_path)

        config_dir = Path(config_path).parent
        schedules_path = config_dir / "schedules.yaml"
        if schedules_path.exists():
            self.config.update(load_config(schedules_path))

        self.mode = self.config.get("mode", "fish")
        if self.mode not in ("fish", "dog"):
            raise ValueError(
                f"Unknown mode {self.mode!r} in {config_path}. "
                "Must be 'fish' or 'dog'."
            )

        # Pick the right persona file for the active mode.
        profile_filename = (
            "dog_profiles.yaml" if self.mode == "dog" else "fish_profiles.yaml"
        )
        profiles_path = config_dir / profile_filename
        self.profiles = (
            load_fish_profiles(profiles_path)
            if profiles_path.exists() else {}
        )

        # Optional detection-label whitelist (drops stray classes from
        # the multi-class COCO base model).
        self.subject_classes = set(self.config.get("subject_classes") or [])

        self.db = FishDB(self.config.get("db_path", "data/fishfluencer.db"))
        self.camera = FishCamera(**self.config.get("camera", {}))
        self.detector = self._init_detector()

        # Tracker — wire state persistence so subject IDs survive a
        # systemd restart.
        tracker_cfg = dict(self.config.get("tracker", {}))
        tracker_cfg.setdefault(
            "state_path",
            self.config.get("tracker_state_path", "data/tracker_state.json"),
        )
        self.tracker = CentroidTracker(**tracker_cfg)

        # Analyzer — span emission model, picks up checkpoint_interval
        # from the same config block.
        self.analyzer = BehaviorAnalyzer(
            **self.config.get("behavior", {}), mode=self.mode
        )
        self.temp_sensor = self._init_temp_sensor()
        self.image_mgr = ImageManager(**self.config.get("images", {}))
        self.summarizer = BehaviorSummarizer(
            self.db,
            self.profiles,
            mode=self.mode,
            checkpoint_interval_seconds=self.analyzer.checkpoint_interval,
        )
        self.alert_summarizer = AlertSummarizer(self.db, self.profiles)
        self.post_gen = PostGenerator(
            api_key=os.environ.get(
                "ANTHROPIC_API_KEY",
                self.config.get("anthropic_api_key", ""),
            ),
            profiles=self.profiles,
            model=self.config.get("anthropic_model", "claude-sonnet-4-6"),
            mode=self.mode,
        )
        self.error_pusher = ErrorLogPusher(
            **self.config.get("error_reporting", {})
        )
        dashboard_cfg = dict(self.config.get("dashboard", {}))
        dashboard_enabled = dashboard_cfg.pop("enabled", True)
        self.dashboard = (
            Dashboard(self.db, **dashboard_cfg) if dashboard_enabled else None
        )

        # Heat-stroke alert config + cooldown bookkeeping.
        alert_cfg = self.config.get("heat_stroke_alert", {})
        self.heat_alert_enabled = bool(alert_cfg.get("enabled", False))
        self.heat_alert_threshold_f = float(
            alert_cfg.get("threshold_f", 85.0)
        )
        self.heat_alert_cooldown_seconds = float(
            alert_cfg.get("cooldown_minutes", 30.0)
        ) * 60
        self._last_heat_alert_ts: float = 0.0
        self._tracker_save_ts: float = time.time()
        self._tracker_save_interval_seconds = 60.0

        self._running = False

    def _init_detector(self):
        """Initialize the Edge TPU detector. If unavailable (e.g. running
        on a dev machine without pycoral), log a warning and return None
        so the rest of the orchestrator still loads.
        """
        try:
            return FishDetector(**self.config.get("detector", {}))
        except Exception as e:  # pycoral missing, model file missing, etc.
            logger.warning(
                "FishDetector unavailable (%s) — inference disabled. "
                "On a real Coral device this is a hard error; on a dev "
                "machine it's expected.", e
            )
            return None

    def _init_temp_sensor(self):
        try:
            return DS18B20(self.config.get("temp_sensor_id"))
        except FileNotFoundError as e:
            logger.warning(
                "DS18B20 not detected (%s) — temperature logging disabled.", e
            )
            return None

    def start(self):
        logger.info("=== FishFluencer starting ===")
        self._running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        if self.dashboard:
            self.dashboard.start()

        try:
            self.camera.open()
        except Exception as e:
            logger.warning(
                "Camera unavailable (%s) — capture loop will be a no-op. "
                "Scheduler still runs.", e
            )

        post_times = self.config.get("post_times", ["09:00", "17:00"])
        for t in post_times:
            schedule.every().day.at(t).do(self._generate_and_post)

        temp_min = self.config.get("temperature_interval_minutes", 5)
        snap_min = self.config.get("snapshot_interval_minutes", 15)
        purge_min = self.config.get("purge_interval_minutes", 60)
        schedule.every(temp_min).minutes.do(self._read_temperature)
        schedule.every(snap_min).minutes.do(self._take_snapshot)
        schedule.every(purge_min).minutes.do(self._purge_images)

        fps_target = self.config.get("inference_fps", 5)
        frame_interval = 1.0 / fps_target

        try:
            while self._running:
                loop_start = time.time()

                try:
                    self._process_frame()
                except Exception as e:
                    logger.error("Frame processing error: %s", e)
                    self.error_pusher.report_error(
                        e, context={"phase": "frame_processing"}
                    )

                schedule.run_pending()

                # Periodically persist tracker state so subject IDs
                # survive a restart. Cheap (writes ~hundreds of bytes
                # of JSON), so do it every minute by default.
                if (
                    time.time() - self._tracker_save_ts
                    >= self._tracker_save_interval_seconds
                ):
                    self.tracker.save_state()
                    self._tracker_save_ts = time.time()

                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.critical("Fatal error: %s", e)
            self.error_pusher.report_error(e, context={"phase": "main_loop"})
        finally:
            # Final flush so the next start picks up the latest IDs.
            try:
                self.tracker.save_state()
            except Exception as e:
                logger.warning("Tracker state save failed: %s", e)
            self.camera.close()
            logger.info("=== FishFluencer stopped ===")

    def _filter_detections(self, detections: list) -> list:
        """Drop detections whose label isn't in the configured whitelist.
        Empty whitelist = pass-through (default)."""
        if not self.subject_classes:
            return detections
        return [d for d in detections if d.label in self.subject_classes]

    def _process_frame(self):
        if self.detector is None:
            time.sleep(0.5)
            return
        try:
            result = self.camera.capture_frame()
        except RuntimeError:
            return
        detections = self._filter_detections(self.detector.detect(result.frame))
        tracked = self.tracker.update(detections)
        behaviors = self.analyzer.analyze(tracked)
        for event in behaviors:
            self.db.log_behavior(event)

    def _take_snapshot(self):
        if self.detector is None:
            return
        try:
            result = self.camera.capture_frame()
        except RuntimeError as e:
            logger.warning("Snapshot skipped: %s", e)
            return
        detections = self._filter_detections(self.detector.detect(result.frame))
        description = self.image_mgr.describe_frame(result.frame, detections)
        filepath = self.camera.save_frame(
            result, self.image_mgr.storage_dir, prefix="scheduled"
        )
        self.db.register_snapshot(
            str(filepath),
            description=description,
            purge_hours=self.config.get("image_retention_hours", 24.0),
        )

    def _read_temperature(self):
        if self.temp_sensor is None:
            return
        try:
            reading = self.temp_sensor.read()
            self.db.log_temperature(reading)
            logger.debug("Temp: %.1f°F", reading.fahrenheit)
        except Exception as e:
            logger.warning("Temp read failed: %s", e)
            return

        self._check_heat_stroke(reading)

    def _check_heat_stroke(self, reading) -> None:
        """If the ambient temperature crosses the configured threshold,
        fire a high-priority alert post. Subject to a cooldown so a
        sustained heat event doesn't spam the social feed."""
        if not self.heat_alert_enabled:
            return
        if reading.fahrenheit < self.heat_alert_threshold_f:
            return
        now = time.time()
        if now - self._last_heat_alert_ts < self.heat_alert_cooldown_seconds:
            logger.info(
                "Heat-stroke threshold crossed (%.1f°F ≥ %.1f°F) but "
                "still in cooldown — skipping alert.",
                reading.fahrenheit, self.heat_alert_threshold_f,
            )
            return
        self._last_heat_alert_ts = now
        logger.warning(
            "HEAT-STROKE ALERT: %.1f°F ≥ %.1f°F — generating alert post",
            reading.fahrenheit, self.heat_alert_threshold_f,
        )
        self._generate_alert_post(reading)

    def _generate_alert_post(self, reading) -> None:
        """Bypass the periodic 12-hour summary and post an immediate
        focused alert. Uses the same publisher path so configured
        social platforms get the alert."""
        try:
            summary = self.alert_summarizer.generate_alert_summary(
                reading, self.heat_alert_threshold_f
            )
            platforms = self.config.get("platforms", ["twitter"])
            character_name = self.config.get("primary_poster", None)

            for platform in platforms:
                post = self.post_gen.generate_post(
                    summary=summary,
                    platform=platform,
                    character_name=character_name,
                )
                logger.warning("[%s] ALERT post: %s...", platform, post[:100])
                publisher = make_publisher(platform)
                try:
                    status = publisher.publish(platform, post)
                    self.db.log_post(
                        platform, post, summary, status=f"alert:{status}"
                    )
                except Exception as pub_err:
                    logger.error(
                        "Alert publish failed (%s): %s", platform, pub_err
                    )
                    self.db.log_post(
                        platform, post, summary,
                        status=f"alert_failed:{pub_err}",
                    )
        except Exception as e:
            logger.error("Alert post generation failed: %s", e)
            self.error_pusher.report_error(
                e, context={"phase": "alert_post"}
            )

    def _generate_and_post(self):
        try:
            summary = self.summarizer.generate_summary(hours=12.0)
            logger.info("Summary generated (%d chars)", len(summary))

            platforms = self.config.get("platforms", ["twitter"])
            character_name = self.config.get("primary_poster", None)

            for platform in platforms:
                post = self.post_gen.generate_post(
                    summary=summary,
                    platform=platform,
                    character_name=character_name,
                )
                logger.info("[%s] Post: %s...", platform, post[:100])

                publisher = make_publisher(platform)
                try:
                    status = publisher.publish(platform, post)
                    self.db.log_post(platform, post, summary, status=status)
                except Exception as pub_err:
                    logger.error("Publish failed (%s): %s", platform, pub_err)
                    self.db.log_post(
                        platform, post, summary, status=f"failed:{pub_err}"
                    )

        except Exception as e:
            logger.error("Post generation failed: %s", e)
            self.error_pusher.report_error(
                e, context={"phase": "post_generation"}
            )

    def _purge_images(self):
        self.image_mgr.purge_expired(self.db)
        self.image_mgr.enforce_storage_limit()

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal received (%s)", signum)
        self._running = False


def main():
    configure_logging(os.environ.get("FISHFLUENCER_LOG_LEVEL", "INFO"))
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    app = FishFluencer(config_path)
    app.start()


if __name__ == "__main__":
    main()
