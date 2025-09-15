import os
import subprocess
import logging
import threading
import time
from datetime import datetime, timedelta
import signal
import glob
import socket
import urllib.parse

logger = logging.getLogger(__name__)

class StreamRecorder:
    def __init__(self, camera_config, storage_path):
        self.name = camera_config['name']
        self.rtsp_url = camera_config['rtsp_url']
        self.codec = camera_config['codec']
        self.interval = camera_config['interval']
        self.process = None
        self.recording = False
        self.last_restart = 0
        self.restart_cooldown = 30
        self.storage_path = storage_path

    def check_camera_connectivity(self):
        logger.debug(f"Checking connectivity for camera: {self.name}")
        try:
            parsed = urllib.parse.urlparse(self.rtsp_url)
            socket.create_connection((parsed.hostname, parsed.port or 554), timeout=3)
            logger.debug(f"Camera {self.name} connectivity check passed")
            return True
        except Exception as e:
            logger.debug(f"Camera {self.name} connectivity check failed: {str(e)}")
            return False

    def get_current_output_dir(self):
        """Get current date directory for output"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        output_dir = f"{self.storage_path}/{self.name}/{current_date}"
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Output directory created/verified: {output_dir}")
        return output_dir

    def start(self):
        if self.recording and self.process and self.process.poll() is None:
            logger.debug(f"Camera {self.name} is already recording, skipping start")
            return

        if not self.check_camera_connectivity():
            logger.warning(f"Camera {self.name} is not reachable")
            return

        logger.info(f"Starting recording for camera: {self.name}")

        output_dir = self.get_current_output_dir()
        output_pattern = f"{output_dir}/%Y-%m-%d_%H-%M-%S.mp4"

        cmd = [
            'ffmpeg',
            '-hide_banner', '-y',
            '-loglevel', 'error',
            '-rtsp_transport', 'tcp',
            '-use_wallclock_as_timestamps', '1',
            '-i', self.rtsp_url,
            #'-cv', self.codec,
            '-c:v copy -c:a mp3 -ar 16000 -ac 1',
            '-f', 'segment',
            '-reset_timestamps', '1',
            '-segment_time', str(self.interval),
            '-segment_format', 'mp4',
            '-segment_atclocktime', '1',
            '-strftime', '1',
            output_pattern
        ]

        logger.debug(f"FFmpeg command for {self.name}: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.debug(f"FFmpeg process started for {self.name}, PID: {self.process.pid}")
            self.recording = True
            self._start_directory_monitor()
            logger.info(f"Recording started for camera: {self.name}")
        except Exception as e:
            logger.error(f"Failed to start recording for {self.name}: {str(e)}")
            self.recording = False

    def _start_directory_monitor(self):
        """Monitor and create new date directories as needed"""
        monitor_thread = threading.Thread(target=self._monitor_directories, daemon=True)
        monitor_thread.start()

    def _monitor_directories(self):
        """Ensure date directories exist, especially during day transitions"""
        logger.debug(f"Directory monitor started for camera: {self.name}")
        while self.recording:
            try:
                # Create directory for current date
                current_date = datetime.now().strftime('%Y-%m-%d')
                current_dir = f"{self.storage_path}/{self.name}/{current_date}"
                logger.debug(f"Creating current date directory for {self.name}: {current_dir}")
                os.makedirs(current_dir, exist_ok=True)

                # If evening hours, also create tomorrow's directory
                current_time = datetime.now()
                if current_time.hour >= 22:
                    next_date = (current_time + timedelta(days=1)).strftime('%Y-%m-%d')
                    next_dir = f"{self.storage_path}/{self.name}/{next_date}"
                    logger.debug(f"Creating next day directory for {self.name}: {next_dir}")
                    os.makedirs(next_dir, exist_ok=True)

            except Exception as e:
                logger.error(f"Error managing directories for {self.name}: {str(e)}")

            time.sleep(3600)  # Check every hour

    def stop(self):
        if self.process:
            self.recording = False
            logger.debug(f"Sending SIGTERM to process {self.process.pid} for camera: {self.name}")
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
                logger.debug(f"Process terminated gracefully for camera: {self.name}")
            except subprocess.TimeoutExpired:
                logger.debug(f"Process timeout, sending SIGKILL to camera: {self.name}")
                self.process.kill()
            self.process = None
            logger.info(f"Stopped recording for camera: {self.name}")
        else:
            logger.debug(f"No process to stop for camera: {self.name}")

    def restart(self):
        logger.debug(f"Restart method called for camera: {self.name}")
        current_time = time.time()
        if current_time - self.last_restart < self.restart_cooldown:
            logger.debug(f"Restart cooldown active for camera: {self.name}, skipping restart")
            return

        logger.info(f"Restarting camera: {self.name}")
        self.stop()
        time.sleep(3)
        self.start()
        self.last_restart = current_time
        logger.debug(f"Restart complete for camera: {self.name}")

    def is_healthy(self):
        # Check if process is running
        if not self.process or self.process.poll() is not None:
            return False

        # Check if camera is reachable
        if not self.check_camera_connectivity():
            return False

        # Check for recent files
        current_time = datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')
        date_dir = f"{self.storage_path}/{self.name}/{current_date}"

        if not os.path.exists(date_dir):
            logger.debug(f"Date directory does not exist for {self.name}: {date_dir}")
            return False

        files = glob.glob(f"{date_dir}/*.mkv")
        for file_path in files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if (current_time - mod_time).total_seconds() < 300:  # 5 minutes
                    logger.debug(f"Recent file found for {self.name}, health check passed")
                    return True
            except Exception as e:
                logger.debug(f"Error checking file modification time for {self.name}: {str(e)}")
                continue

        logger.debug(f"No recent files found for {self.name}, health check failed")
        return False

    def get_individual_health(self):
        """Get detailed health status for this camera"""
        process_running = self.process is not None and self.process.poll() is None
        camera_reachable = self.check_camera_connectivity()
        recent_files = False

        current_time = datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')
        date_dir = f"{self.storage_path}/{self.name}/{current_date}"

        if os.path.exists(date_dir):
            files = glob.glob(f"{date_dir}/*.mkv")
            for file_path in files:
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (current_time - mod_time).total_seconds() < 300:
                        recent_files = True
                        break
                except Exception:
                    continue

        return {
            'name': self.name,
            'process_running': process_running,
            'recent_files': recent_files,
            'camera_reachable': camera_reachable,
            'recording': self.recording,
            'healthy': process_running and recent_files and camera_reachable
        }
