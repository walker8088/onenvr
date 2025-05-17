import os
import sys
import glob
import time
import logging
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def check_ffmpeg_processes():
    """Check if ffmpeg processes are running for recording"""
    try:
        # Use ps command to look for ffmpeg processes
        result = subprocess.run(
            ['ps', '-ef'],
            capture_output=True,
            text=True
        )

        # Check if there are any ffmpeg processes running for recording
        ffmpeg_processes = [line for line in result.stdout.split('\n')
                         if 'ffmpeg' in line and 'segment' in line]

        if not ffmpeg_processes:
            logger.error("No ffmpeg recording processes found")
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking ffmpeg processes: {str(e)}")
        return False

def check_health():
    # Check 1: Verify storage directory exists and is writable
    if not os.path.exists('/storage') or not os.access('/storage', os.W_OK):
        print("Storage directory not accessible")
        return False

    # Check 2: Verify config directory exists and is readable
    if not os.path.exists('/config') or not os.access('/config', os.R_OK):
        print("Config directory not accessible")
        return False

    # Check 3: Check for web server connection and response
    try:
        import urllib.request
        import urllib.error
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as response:
            if response.getcode() != 200:
                print(f"Web server returned unexpected status: {response.getcode()}")
                return False
    except urllib.error.URLError as e:
        print(f"Web server connection failed: {str(e.reason)}")
        return False
    except Exception as e:
        print(f"Error checking web server: {str(e)}")
        return False

    # Check 4: Check for ffmpeg processes
    if not check_ffmpeg_processes():
        print("No active recording processes found")
        return False

    # Check 5: Check for recent recordings in the last 2 minutes
    now = datetime.now()
    recent_files_found = False

    for camera_dir in glob.glob('/storage/*/raw'):
        files = glob.glob(f"{camera_dir}/*.mkv")
        for f in files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(f))
                if now - mod_time < timedelta(minutes=2):
                    recent_files_found = True
                    break
            except Exception as e:
                print(f"Error checking file timestamp: {str(e)}")
        if recent_files_found:
            break

    if not recent_files_found:
        print("No recent recordings found")
        return False

    return True

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
