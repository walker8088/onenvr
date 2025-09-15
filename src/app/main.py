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

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

class NVRSystem:
    def __init__(self, config_path):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OneNVR system")
        self.config = load_config(config_path)
        self.storage_path = self.config['storage_path']
        self.recorders = {}
        self.video_manager = VideoManager(self.config)
        self.setup_recorders()
        self.setup_schedules()
        self.start_web_server()

    def setup_recorders(self):
        self.logger.debug(f"Setting up recorders for {len(self.config['cameras'])} cameras")
        for camera_config in self.config['cameras']:
            camera_name = camera_config['name']
            self.recorders[camera_name] = StreamRecorder(camera_config, self.storage_path)
        self.video_manager.set_recorders(self.recorders)
        self.logger.debug("All recorders setup complete")

    def setup_schedules(self):
        self.logger.debug("Setting up scheduled tasks")
        if self.config['concatenation']:
            schedule.every().day.at(self.config['concatenation_time']).do(self.concatenate_all_cameras)

        schedule.every().day.at(self.config['deletion_time']).do(
            self.video_manager.cleanup_old_recordings
        )

        # Health checks and maintenance
        schedule.every(2).minutes.do(self.health_check)
        self.logger.debug("Schedule setup complete")

    def initial_directories(self):
        """Create directory for current date for all cameras"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        self.logger.debug(f"Creating initial directories for date: {current_date}")

        for camera_name in self.recorders.keys():
            date_dir = f"{self.storage_path}/{camera_name}/{current_date}"
            os.makedirs(date_dir, exist_ok=True)
            self.logger.debug(f"Directory created/verified: {date_dir}")

    def start(self):
        self.logger.info("Starting OneNVR recorders")

        # Ensure initial directories exist
        self.initial_directories()

        for recorder in self.recorders.values():
            recorder.start()

        # Main loop
        self.logger.debug("Entering main loop")
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                time.sleep(5)

    def stop(self):
        self.logger.info("Stopping OneNVR system")
        for recorder in self.recorders.values():
            recorder.stop()
        self.logger.debug("All recorders stopped")

    def health_check(self):
        self.logger.debug("Starting health check for all cameras")
        for name, recorder in self.recorders.items():
            self.logger.debug(f"Checking health for camera: {name}")
            if not recorder.is_healthy():
                self.logger.warning(f"Restarting unhealthy camera: {name}")
                recorder.restart()
            else:
                self.logger.debug(f"Camera {name} is healthy")

    def concatenate_all_cameras(self):
        self.logger.info("Starting daily video concatenation")
        for camera_name in self.recorders.keys():
            self.logger.debug(f"Starting concatenation for camera: {camera_name}")
            self.video_manager.concatenate_daily_videos(camera_name)
        self.logger.debug("Daily concatenation complete for all cameras")

    def start_web_server(self):
        self.logger.debug("Creating web server")
        self.web_app = create_web_server(self.config)
        self.logger.debug("Starting web server thread")
        server_thread = threading.Thread(
            target=self.web_app.run,
            kwargs={'host': '0.0.0.0', 'port': 5000, 'threaded': True},
            daemon=True
        )
        server_thread.start()
        self.logger.info("OneNVR web server started")

if __name__ == "__main__":
    try:
        nvr = NVRSystem('config')
        nvr.start()
    except Exception as e:
        logger.error(f"Failed to start OneNVR system: {str(e)}")
