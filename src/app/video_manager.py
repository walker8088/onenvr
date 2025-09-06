import os
import subprocess
import logging
from datetime import datetime, timedelta
import glob

logger = logging.getLogger(__name__)

class VideoManager:
    def __init__(self, retention_days):
        self.retention_days = retention_days
        self.recorders = {}

    def set_recorders(self, recorders):
        self.recorders = recorders

    def concatenate_daily_videos(self, camera_name):
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        date_dir = f"/storage/{camera_name}/{yesterday}"

        if not os.path.exists(date_dir):
            logger.info(f"No directory found for {camera_name} on {yesterday}")
            return

        input_pattern = f"{date_dir}/*.mkv"
        output_file = f"{date_dir}/{camera_name}_{yesterday}.mkv"

        # Get all individual segment files (exclude already concatenated files)
        video_files = [f for f in sorted(glob.glob(input_pattern))
                      if not f.endswith(f"{camera_name}_{yesterday}.mkv")]

        if not video_files:
            logger.info(f"No videos to concatenate for {camera_name} on {yesterday}")
            return

        try:
            # Create file list for ffmpeg
            filelist_path = f"/tmp/filelist_{camera_name}_{yesterday}.txt"
            with open(filelist_path, 'w') as f:
                for video in video_files:
                    f.write(f"file '{os.path.abspath(video)}'\n")

            # Concatenate videos with low I/O priority
            cmd = [
                'ionice',
                '-c', '2',
                '-n', '7',
                'ffmpeg',
                '-hide_banner', '-y',
                '-loglevel', 'error',
                '-f', 'concat',
                '-safe', '0',
                '-i', filelist_path,
                '-c', 'copy',
                output_file
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully concatenated videos for {camera_name} on {yesterday}")

            # Clean up individual segments after successful concatenation
            for video in video_files:
                os.remove(video)

            # Clean up filelist
            os.remove(filelist_path)

        except Exception as e:
            logger.error(f"Failed to concatenate videos for {camera_name}: {str(e)}")
            # Clean up filelist on error
            if os.path.exists(filelist_path):
                os.remove(filelist_path)

    def cleanup_old_recordings(self):
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        logger.info(f"Cleaning up recordings older than {cutoff_date.strftime('%Y-%m-%d')}")

        removed_count = 0
        for camera_dir in glob.glob('/storage/*/'):
            camera_name = os.path.basename(camera_dir.rstrip('/'))

            for date_dir in glob.glob(f"{camera_dir}*/"):
                dir_name = os.path.basename(date_dir.rstrip('/'))

                # Skip non-date directories
                if dir_name == 'raw':
                    continue

                try:
                    dir_date = datetime.strptime(dir_name, '%Y-%m-%d')
                    if dir_date < cutoff_date:
                        # Remove all files in the directory
                        for file_path in glob.glob(f"{date_dir}*"):
                            os.remove(file_path)
                        # Remove the directory
                        os.rmdir(date_dir)
                        logger.info(f"Removed old recordings: {date_dir}")
                        removed_count += 1
                except (ValueError, OSError) as e:
                    logger.warning(f"Could not process directory {date_dir}: {str(e)}")
                    continue

        if removed_count == 0:
            logger.info("No old recordings found to delete")
