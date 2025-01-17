import os
import subprocess
import logging
from datetime import datetime
import signal
import glob

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

    def start(self):
        if self.recording:
            return

        logger.info(f"Starting recording for camera: {self.name}")
        # Record to raw directory with just timestamp filename
        output_pattern = f"{self.raw_dir}/%H-%M-%S.mkv"

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
            # Start the file mover thread
            self._start_file_mover()
        except Exception as e:
            logger.error(f"Failed to start recording for {self.name}: {str(e)}")

    def _start_file_mover(self):
        """Start a thread to periodically move completed segments to date directories"""
        import threading
        self.mover_thread = threading.Thread(target=self._move_segments, daemon=True)
        self.mover_thread.start()

    def _move_segments(self):
        """Periodically move completed segments to their date-based directories"""
        import time
        while self.recording:
            try:
                self._process_raw_segments()
            except Exception as e:
                logger.error(f"Error moving segments for {self.name}: {str(e)}")
            time.sleep(30)  # Check every 30 seconds

    def _process_raw_segments(self):
        """Move completed segments to their date directories"""
        current_time = datetime.now()
        raw_files = glob.glob(f"{self.raw_dir}/*.mkv")

        for raw_file in raw_files:
            try:
                # Get file modification time
                mod_time = datetime.fromtimestamp(os.path.getmtime(raw_file))

                # If file is still being written to (modified in last interval), skip it
                if (current_time - mod_time).total_seconds() < self.interval:
                    continue

                # Create date directory if it doesn't exist
                date_str = mod_time.strftime('%Y-%m-%d')
                date_dir = f"/storage/{self.name}/{date_str}"
                os.makedirs(date_dir, exist_ok=True)

                # Move file to date directory
                filename = os.path.basename(raw_file)
                new_path = os.path.join(date_dir, filename)
                os.rename(raw_file, new_path)
                logger.debug(f"Moved {filename} to {date_dir}")

            except Exception as e:
                logger.error(f"Error processing {raw_file}: {str(e)}")

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()
            self.process = None
            self.recording = False
            # Process any remaining files
            try:
                self._process_raw_segments()
            except Exception as e:
                logger.error(f"Error processing remaining segments: {str(e)}")

    def is_healthy(self):
        return self.process is not None and self.process.poll() is None
