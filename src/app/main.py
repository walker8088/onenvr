import os
import schedule
import time
import threading
from datetime import datetime, timedelta
from config import load_config, setup_logging
from recorder import StreamRecorder
from video_manager import VideoManager
from web_interface import create_web_server
import logging
import glob

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

class NVRSystem:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OneNVR system")
        self.config = load_config()
        self.recorders = {}
        self.video_manager = VideoManager(self.config['retention_days'])
        self.web_app = None
        self.setup_recorders()
        self.setup_schedules()
        self.start_web_server()

    def setup_recorders(self):
        # First ensure base storage directories exist
        logger.debug(f"Creating base directories for all cameras")
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
        logger.debug(f"Setting up schedules for all cameras")
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
        else:
            logger.info("Concatenation is disabled in the configuration")

        schedule.every().day.at(self.config['deletion_time']).do(
            self.video_manager.cleanup_old_recordings
        )
        logger.info(f"Deletion of recordings older than {self.config['retention_days']} days scheduled at {self.config['deletion_time']} every day")

        # Add periodic segment processing
        schedule.every(5).minutes.do(self.process_all_segments)

        # Add periodic health check
        schedule.every(1).minutes.do(self.health_check)

    def process_all_segments(self):
        # Process any completed segments for all cameras
        logger.debug(f"Processing completed segments for all cameras")
        for recorder in self.recorders.values():
            try:
                recorder._process_raw_segments()
            except Exception as e:
                logger.error(f"Error processing segments for {recorder.name}: {str(e)}")

    def start(self):
        logger.info(f"Starting OneNVR recorders")
        for recorder in self.recorders.values():
            recorder.start()

        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(5)

    def stop(self):
        logger.info(f"Stopping OneNVR system")
        for recorder in self.recorders.items():
            recorder.stop()

        # Process any final segments
        self.process_all_segments()

    def health_check(self):
        logger.debug("Running health check")
        for name, recorder in self.recorders.items():
            # First check if it's healthy
            is_healthy = recorder.is_healthy()

            if not is_healthy and recorder.needs_restart():
                logger.warning(f"{name} recording is not healthy, attempting restart...")
                recorder.stop()
                time.sleep(2)  # Allow time for cleanup
                recorder.start()
                logger.info(f"Restart attempted for {name}")

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

    def start_web_server(self):
        self.web_app = create_web_server()

        server_thread = threading.Thread(
            target=self.web_app.run,
            kwargs={
                'host': '0.0.0.0',
                'port': 5000,
                'threaded': True
            },
            daemon=True
        )
        server_thread.start()
        logger.info(f"OneNVR web server started")

if __name__ == "__main__":
    try:
        nvr = NVRSystem()
        nvr.start()
    except Exception as e:
        logger.error(f"Failed to start OneNVR system: {str(e)}")
