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
        self.restart_cooldown = 30
        self.restart_needed = False
        self.last_file_time = None

    def check_camera_connectivity(self):
        try:
            parsed = urllib.parse.urlparse(self.rtsp_url)
            socket.create_connection((parsed.hostname, parsed.port or 554), timeout=3)
            return True
        except Exception:
            return False

    def start(self):
        if self.process is None or self.process.poll() is not None:
            self.recording = False

        if self.recording:
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
        # Record to raw directory with date and time in filename
        output_pattern = f"{self.raw_dir}/%Y-%m-%d_%H-%M-%S.mkv"

        # Ensure raw directory exists
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
            logger.debug(f"Executing command: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.recording = True
            self.restart_needed = False
            self.last_file_time = datetime.now()
            # Start the file mover thread
            self._start_file_mover()
            logger.info(f"Recording initiated for camera: {self.name}")
        except Exception as e:
            logger.error(f"Failed to start recording for {self.name}: {str(e)}")
            self.restart_needed = True  # Mark for restart if start fails

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
            time.sleep(30)  # Check every 30 seconds

    def _process_raw_segments(self):
        # Move completed segments to their date directories
        current_time = datetime.now()
        raw_files = glob.glob(f"{self.raw_dir}/*.mkv")

        for raw_file in raw_files:
            try:
                # Get file modification time to check if file is complete
                mod_time = datetime.fromtimestamp(os.path.getmtime(raw_file))

                # If file is still being written to (modified in last interval), skip it
                if (current_time - mod_time).total_seconds() < self.interval:
                    continue

                # Get date from filename
                filename = os.path.basename(raw_file)
                date_str = filename.split('_')[0]

                # Create date directory if it doesn't exist
                date_dir = f"/storage/{self.name}/{date_str}"
                os.makedirs(date_dir, exist_ok=True)

                # Move file to date directory
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
                self.last_file_time = current_time
                logger.debug(f"Moved {filename} to {date_dir}")

            except Exception as e:
                logger.error(f"Error processing {raw_file}: {str(e)}")

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()

            self.process = None
            self.recording = False
            # Process any remaining files
            try:
                self._process_raw_segments()
            except Exception as e:
                logger.error(f"Error processing remaining segments: {str(e)}")

    def is_healthy(self):
        current_time = time.time()

        # Check if process is running
        process_healthy = self.process is not None and self.process.poll() is None

        # Check if we're getting recent files (within 2x interval + 30 seconds buffer)
        files_healthy = True
        if self.last_file_time:
            time_since_last_file = (datetime.now() - self.last_file_time).total_seconds()
            files_healthy = time_since_last_file < (self.interval * 2 + 30)

        # If both process and files are healthy, all is well
        if process_healthy and files_healthy:
            self.restart_needed = False
            return True

        # Something is unhealthy - check if restart is needed
        # Do not attempt restart if in cooldown period
        if current_time - self.last_restart_attempt < self.restart_cooldown:
            return False

        # Check if camera is reachable
        camera_reachable = self.check_camera_connectivity()

        if camera_reachable:
            # Camera is reachable but recording is unhealthy, mark for restart
            self.restart_needed = True
            self.last_restart_attempt = current_time
            logger.warning(f"Camera {self.name} is unhealthy but reachable - marking for restart")
            return False
        else:
            # Camera is unreachable, cannot restart
            logger.warning(f"Camera {self.name} is unreachable")
            self.restart_needed = False
            self.last_restart_attempt = current_time
            return False

    def needs_restart(self):
        # Check if this recorder needs to be restarted
        return self.restart_needed

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
                if (current_time - mod_time).total_seconds() < 120:
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
            'healthy': process_running and recent_files and camera_reachable
        }
