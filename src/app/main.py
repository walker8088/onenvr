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
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OneNVR system")
        self.config = load_config()
        self.recorders = {}
        self.video_manager = VideoManager(self.config['retention_days'])
        self.setup_recorders()
        self.setup_schedules()
        self.start_web_server()

    def setup_recorders(self):
        for camera_config in self.config['cameras']:
            camera_name = camera_config['name']
            self.recorders[camera_name] = StreamRecorder(camera_config)
        self.video_manager.set_recorders(self.recorders)

    def setup_schedules(self):
        if self.config['concatenation']:
            schedule.every().day.at(self.config['concatenation_time']).do(self.concatenate_all_cameras)

        schedule.every().day.at(self.config['deletion_time']).do(
            self.video_manager.cleanup_old_recordings
        )

        # Health checks and maintenance
        schedule.every(2).minutes.do(self.health_check)

    def initial_directories(self):
        """Create directory for current date for all cameras"""
        current_date = datetime.now().strftime('%Y-%m-%d')

        for camera_name in self.recorders.keys():
            date_dir = f"/storage/{camera_name}/{date_str}"
            os.makedirs(date_dir, exist_ok=True)

    def start(self):
        self.logger.info("Starting OneNVR recorders")

        # Ensure initial directories exist
        self.initial_directories()

        for recorder in self.recorders.values():
            recorder.start()

        # Main loop
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

    def health_check(self):
        for name, recorder in self.recorders.items():
            if not recorder.is_healthy():
                self.logger.warning(f"Restarting unhealthy camera: {name}")
                recorder.restart()

    def concatenate_all_cameras(self):
        self.logger.info("Starting daily video concatenation")
        for camera_name in self.recorders.keys():
            self.video_manager.concatenate_daily_videos(camera_name)

    def start_web_server(self):
        self.web_app = create_web_server()
        server_thread = threading.Thread(
            target=self.web_app.run,
            kwargs={'host': '0.0.0.0', 'port': 5000, 'threaded': True},
            daemon=True
        )
        server_thread.start()
        self.logger.info("OneNVR web server started")

if __name__ == "__main__":
    try:
        nvr = NVRSystem()
        nvr.start()
    except Exception as e:
        logger.error(f"Failed to start OneNVR system: {str(e)}")
