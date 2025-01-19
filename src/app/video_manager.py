import os
import subprocess
import logging
from datetime import datetime, timedelta
import glob

logger = logging.getLogger(__name__)

class VideoManager:
    def __init__(self, retention_days):
        # Initialize VideoManager with retention policy.
        self.retention_days = retention_days
        self.recorders = {}

    def set_recorders(self, recorders):
        # Store reference to recorder instances
        self.recorders = recorders

    def _get_recorder(self, camera_name):
        # Get recorder instance for a camera
        return self.recorders.get(camera_name)

    def concatenate_daily_videos(self, camera_name):
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        date_dir = f"/storage/{camera_name}/{yesterday}"
        raw_dir = f"/storage/{camera_name}/raw"

        # First, ensure all completed segments are moved
        recorder = self._get_recorder(camera_name)
        if recorder:
            recorder._process_raw_segments()

        input_pattern = f"{date_dir}/*.mkv"
        output_file = f"{date_dir}/daily_{yesterday}.mkv"

        if not glob.glob(input_pattern):
            logger.info(f"No videos to concatenate for {camera_name} on {yesterday}")
            return

        try:
            # Create file list for ffmpeg
            with open('filelist.txt', 'w') as f:
                for video in sorted(glob.glob(input_pattern)):
                    if 'daily_' not in video:
                        f.write(f"file '{os.path.abspath(video)}'\n")

            # Concatenate videos
            cmd = [
                'ionice',
                '-c', '2',
                '-n', '7',
                'ffmpeg',
                '-hide_banner', '-y',
                '-loglevel', 'warning',
                '-f', 'concat',
                '-safe', '0',
                '-i', 'filelist.txt',
                '-c', 'copy',
                output_file
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully concatenated videos for {camera_name} on {yesterday}")

            # Clean up individual segments
            for video in glob.glob(input_pattern):
                if 'daily_' not in video:
                    os.remove(video)

        except Exception as e:
            logger.error(f"Failed to concatenate videos for {camera_name}: {str(e)}")
        finally:
            if os.path.exists('filelist.txt'):
                os.remove('filelist.txt')

    def cleanup_old_recordings(self):
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        logger.info(f"Cleaning up recordings older than {cutoff_date}")

        for camera_dir in glob.glob('/storage/*/'):
            for date_dir in glob.glob(f"{camera_dir}*/"):
                try:
                    dir_date = datetime.strptime(os.path.basename(date_dir.rstrip('/')), '%Y-%m-%d')
                    if dir_date < cutoff_date:
                        for file in glob.glob(f"{date_dir}*"):
                            os.remove(file)
                        os.rmdir(date_dir)
                        logger.info(f"Removed old recordings in {date_dir}")
                except ValueError:
                    continue
