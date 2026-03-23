"""
FishFluencer main entry point.

Ties together all subsystems:
  - Camera capture
  - Edge TPU inference
  - Fish tracking + behavior analysis
  - Temperature monitoring
  - Text summary generation
  - Claude API post generation
  - Image lifecycle management
  - Error reporting
"""

import sys
import time
import signal
import logging

import schedule

from capture.camera import FishCamera
from capture.temperature import DS18B20
from data.db import FishDB
from data.image_manager import ImageManager
from data.summarizer import BehaviorSummarizer
from inference.behavior import BehaviorAnalyzer
from inference.detector import FishDetector
from inference.tracker import CentroidTracker
from social.post_generator import PostGenerator
from sync.log_pusher import ErrorLogPusher
from utils.config import load_config
from utils.log import setup_logging

logger = logging.getLogger("fishfluencer")


class FishFluencer:
    def __init__(self, config_path: str = "config/default.yaml"):
        self.config = load_config(config_path)

        self.db = FishDB(self.config.get("db_path", "data/fishfluencer.db"))
        self.camera = FishCamera(**self.config.get("camera", {}))
        self.detector = FishDetector(**self.config.get("detector", {}))
        self.tracker = CentroidTracker(**self.config.get("tracker", {}))
        self.analyzer = BehaviorAnalyzer(**self.config.get("behavior", {}))
        self.temp_sensor = DS18B20(self.config.get("temp_sensor_id"))
        self.image_mgr = ImageManager(**self.config.get("images", {}))
        self.summarizer = BehaviorSummarizer(
            self.db, self.config.get("fish_profiles", {})
        )
        self.post_gen = PostGenerator(
            api_key=self.config["anthropic_api_key"],
            fish_profiles=self.config.get("fish_profiles", {}),
        )
        self.error_pusher = ErrorLogPusher(**self.config.get("error_reporting", {}))

        self._running = False

    def start(self):
        """Start the main processing loop and scheduled tasks."""
        logger.info("=== FishFluencer starting ===")
        self._running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        self.camera.open()

        post_times = self.config.get("post_times", ["09:00", "17:00"])
        for t in post_times:
            schedule.every().day.at(t).do(self._generate_and_post)

        schedule.every(5).minutes.do(self._read_temperature)
        schedule.every(15).minutes.do(self._take_snapshot)
        schedule.every(1).hours.do(self._purge_images)

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

                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.critical("Fatal error: %s", e)
            self.error_pusher.report_error(e, context={"phase": "main_loop"})
        finally:
            self.camera.close()
            logger.info("=== FishFluencer stopped ===")

    def _process_frame(self):
        """Capture → Detect → Track → Analyze (single frame)."""
        result = self.camera.capture_frame()
        detections = self.detector.detect(result.frame)
        tracked = self.tracker.update(detections)
        behaviors = self.analyzer.analyze(tracked)

        for event in behaviors:
            self.db.log_behavior(event)

    def _take_snapshot(self):
        """Save a snapshot with text description for later summarization."""
        result = self.camera.capture_frame()
        detections = self.detector.detect(result.frame)
        description = self.image_mgr.describe_frame(result.frame, detections)

        filepath = self.camera.save_snapshot(
            self.image_mgr.storage_dir, prefix="scheduled"
        )
        self.db.register_snapshot(
            str(filepath),
            description=description,
            purge_hours=self.config.get("image_retention_hours", 24.0),
        )

    def _read_temperature(self):
        """Read and log water temperature."""
        try:
            reading = self.temp_sensor.read()
            self.db.log_temperature(reading)
            logger.debug("Temp: %s°F", reading.fahrenheit)
        except Exception as e:
            logger.warning("Temp read failed: %s", e)

    def _generate_and_post(self):
        """Generate text summary → Claude API → publish post."""
        try:
            summary = self.summarizer.generate_summary(hours=12.0)
            logger.info("Summary generated (%d chars)", len(summary))

            platforms = self.config.get("platforms", ["twitter"])
            fish_name = self.config.get("primary_poster", None)

            for platform_name in platforms:
                post = self.post_gen.generate_post(
                    summary=summary,
                    platform=platform_name,
                    character_name=fish_name,
                )
                logger.info("[%s] Post: %s...", platform_name, post[:100])
                self.db.log_post(platform_name, post, summary)

        except Exception as e:
            logger.error("Post generation failed: %s", e)
            self.error_pusher.report_error(
                e, context={"phase": "post_generation"}
            )

    def _purge_images(self):
        """Delete expired images from disk."""
        self.image_mgr.purge_expired(self.db)
        self.image_mgr.enforce_storage_limit()

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal received (%s)", signum)
        self._running = False


if __name__ == "__main__":
    setup_logging()
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    app = FishFluencer(config_path)
    app.start()
