import os
import subprocess
import logging
import shutil
import threading
import time
from datetime import datetime
import signal
import glob
import socket
import urllib.parse

logger = logging.getLogger(__name__)

class StreamRecorder:
    def __init__(self, camera_config):
        self.name = camera_config['name']
        self.rtsp_url = camera_config['rtsp_url']
        self.codec = camera_config['codec']
        self.interval = camera_config['interval']
        self.process = None
        self.recording = False
        self.raw_dir = f"/storage/{self.name}/raw"
        self.last_restart_attempt = 0
        self.restart_cooldown = 60

    def check_camera_connectivity(self):
        try:
            parsed = urllib.parse.urlparse(self.rtsp_url)
            socket.create_connection((parsed.hostname, parsed.port or 554), timeout=3)
            return True
        except Exception:
            return False

    def start(self):
        if self.recording and self.process and self.process.poll() is None:
            return

        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            if self.check_camera_connectivity():
                break
            logger.warning(f"Waiting for camera {self.name} to be reachable (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            logger.error(f"Failed to connect to camera {self.name} after {max_retries} attempts")
            return

        logger.info(f"Starting recording for camera: {self.name}")
        output_pattern = f"{self.raw_dir}/%Y-%m-%d_%H-%M-%S.mkv"
        logger.debug(f"Creating raw directory for {self.name}")
        os.makedirs(self.raw_dir, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-hide_banner', '-y',
            '-loglevel', 'error',
            '-rtsp_transport', 'tcp',
            '-use_wallclock_as_timestamps', '1',
            '-i', self.rtsp_url,
            '-c', self.codec,
            '-f', 'segment',
            '-reset_timestamps', '1',
            '-segment_time', str(self.interval),
            '-segment_format', 'mkv',
            '-segment_atclocktime', '1',
            '-strftime', '1',
            output_pattern
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.recording = True
            self._start_file_mover()
            logger.info(f"Recording started for camera: {self.name}")
        except Exception as e:
            logger.error(f"Failed to start recording for {self.name}: {str(e)}")
            self.recording = False

    def _start_file_mover(self):
        # Start a thread to periodically move completed segments to date directories
        self.mover_thread = threading.Thread(target=self._move_segments, daemon=True)
        self.mover_thread.start()

    def _move_segments(self):
        # Periodically move completed segments to their date-based directories
        while self.recording:
            try:
                self._process_raw_segments()
            except Exception as e:
                logger.error(f"Error moving segments for {self.name}: {str(e)}")
            time.sleep(30)

    def _process_raw_segments(self):
        # Move completed segments to their date directories
        current_time = datetime.now()
        raw_files = glob.glob(f"{self.raw_dir}/*.mkv")

        for raw_file in raw_files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(raw_file))
                if (current_time - mod_time).total_seconds() < self.interval:
                    continue

                filename = os.path.basename(raw_file)
                date_str = filename.split('_')[0]
                date_dir = f"/storage/{self.name}/{date_str}"
                os.makedirs(date_dir, exist_ok=True)
                new_path = os.path.join(date_dir, filename)

                # Verify read access to source and write access to destination
                if not os.access(raw_file, os.R_OK):
                    raise IOError(f"No read permission for source file: {raw_file}")
                if not os.access(os.path.dirname(new_path), os.W_OK):
                    raise IOError(f"No write permission for destination directory: {os.path.dirname(new_path)}")
                # Verify enough space exists at destination
                if os.path.getsize(raw_file) > shutil.disk_usage(date_dir).free:
                    raise IOError(f"Not enough space at destination: {date_dir}")

                shutil.move(raw_file, new_path)
                logger.debug(f"Moved {filename} to {date_dir}")

            except Exception as e:
                logger.error(f"Error processing {raw_file}: {str(e)}")

    def stop(self):
        if self.process:
            self.recording = False
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

            try:
                self._process_raw_segments()
            except Exception as e:
                logger.error(f"Error processing remaining segments: {str(e)}")

    def is_healthy(self):
        # Process running check
        if not self.process or self.process.poll() is not None:
            return False

        # Recent files check
        current_time = datetime.now()
        raw_files = glob.glob(f"{self.raw_dir}/*.mkv")

        for raw_file in raw_files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(raw_file))
                if (current_time - mod_time).total_seconds() < 180:  # 3 minutes
                    return True
            except Exception:
                continue

        return False

    def needs_restart(self):
        current_time = time.time()
        if current_time - self.last_restart_attempt < self.restart_cooldown:
            return False

        if not self.is_healthy() and self.check_camera_connectivity():
            return True

        return False

    def mark_restart_attempted(self):
        self.last_restart_attempt = time.time()

    def get_individual_health(self):
        # Get detailed health status for this specific camera
        current_time = datetime.now()
        # Check process status
        process_running = self.process is not None and self.process.poll() is None
        # Check for recent files
        recent_files = False
        raw_files = glob.glob(f"{self.raw_dir}/*.mkv")
        for raw_file in raw_files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(raw_file))
                if (current_time - mod_time).total_seconds() < 180:
                    recent_files = True
                    break
            except Exception:
                continue
        # Check camera connectivity
        camera_reachable = self.check_camera_connectivity()

        return {
            'name': self.name,
            'process_running': process_running,
            'recent_files': recent_files,
            'camera_reachable': camera_reachable,
            'recording': self.recording,
            'healthy': process_running and recent_files
        }
