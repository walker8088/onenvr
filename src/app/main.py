import os
import schedule
import time
from datetime import datetime, timedelta
from config import load_config, setup_logging
from recorder import StreamRecorder
from video_manager import VideoManager
import logging
import glob

logger = logging.getLogger(__name__)

class NVRSystem:
    def __init__(self):
        setup_logging()
        self.config = load_config()
        self.recorders = {}
        self.video_manager = VideoManager(self.config['retention_days'])
        self.setup_recorders()
        self.setup_schedules()

    def setup_recorders(self):
        # First ensure base storage directories exist
        for camera_config in self.config['cameras']:
            camera_name = camera_config['name']
            base_dir = f"/storage/{camera_name}"
            raw_dir = f"{base_dir}/raw"
            os.makedirs(base_dir, exist_ok=True)
            os.makedirs(raw_dir, exist_ok=True)

            # Create and store recorder instance
            self.recorders[camera_name] = StreamRecorder(camera_config)

        # Make video manager aware of recorders
        self.video_manager.set_recorders(self.recorders)

    def setup_schedules(self):
        if self.config['concatenation']:
            # Add a delay to ensure all segments are moved before concatenation
            concat_time = datetime.strptime(self.config['concatenation_time'], '%H:%M')
            process_time = (concat_time - timedelta(minutes=5)).strftime('%H:%M')

            # Schedule final segment processing before concatenation
            schedule.every().day.at(process_time).do(
                self.process_all_segments
            )

            schedule.every().day.at(self.config['concatenation_time']).do(
                self.concatenate_all_cameras
            )

        schedule.every().day.at(self.config['deletion_time']).do(
            self.video_manager.cleanup_old_recordings
        )

        # Add periodic segment processing
        schedule.every(5).minutes.do(self.process_all_segments)

    def process_all_segments(self):
        """Process any completed segments for all cameras"""
        logger.info("Processing completed segments for all cameras")
        for recorder in self.recorders.values():
            try:
                recorder._process_raw_segments()
            except Exception as e:
                logger.error(f"Error processing segments for {recorder.name}: {str(e)}")

    def start(self):
        logger.info("Starting OneNVR system")
        for recorder in self.recorders.values():
            recorder.start()

        while True:
            try:
                self.health_check()
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(5)

    def stop(self):
        logger.info("Stopping OneNVR system")
        for recorder in self.recorders.values():
            recorder.stop()

        # Process any final segments
        self.process_all_segments()

    def health_check(self):
        for name, recorder in self.recorders.items():
            if not recorder.is_healthy():
                logger.warning(f"{name} recording is not healthy, restarting...")
                recorder.stop()
                recorder.start()

    def concatenate_all_cameras(self):
        # Ensure all segments are processed first
        self.process_all_segments()
        # Wait a short time to ensure file operations are complete
        time.sleep(5)
        # Now concatenate
        logger.info(f"Starting daily video concatenation")
        for camera_name in self.recorders.keys():
            logger.info(f"Concatenating videos for {camera_name}")
            self.video_manager.concatenate_daily_videos(camera_name)
            time.sleep(10)

if __name__ == "__main__":
    try:
        nvr = NVRSystem()
        nvr.start()
    except Exception as e:
        logger.error(f"Failed to start OneNVR system: {str(e)}")
