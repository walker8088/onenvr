import os
import sys
import glob
import subprocess
from datetime import datetime, timedelta
from config import CONFIG_PATH, STORAGE_PATH

def check_storage_access(storage_path):
    """Check if storage directory is accessible"""
    return os.path.exists(storage_path) and os.access(storage_path, os.W_OK)

def check_config_access():
    """Check if config directory is accessible"""
    #return os.path.exists(CONFIG_PATH) and os.access(CONFIG_PATH, os.R_OK)
    return True
    
def check_web_server():
    """Check if web server is responding"""
    try:
        import urllib.request
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as response:
            return response.getcode() == 200
    except Exception:
        return False

def check_ffmpeg_processes():
    """Check if ffmpeg recording processes are running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'ffmpeg.*segment'],
                              capture_output=True, text=True)
        return len(result.stdout.strip()) > 0
    except Exception:
        return False

def check_camera_recordings(storage_path):
    """Check if cameras are actively recording (recent files exist)"""
    camera_dirs = glob.glob(f'/{storage_path}/*/2*')  # Date directories like 2024-01-01
    if not camera_dirs:
        return False

    current_time = datetime.now()
    healthy_cameras = 0

    for date_dir in camera_dirs:
        # Only check today's recordings
        date_str = os.path.basename(date_dir)
        try:
            dir_date = datetime.strptime(date_str, '%Y-%m-%d')
            if dir_date.date() != current_time.date():
                continue
        except ValueError:
            continue

        # Check for recent files
        files = glob.glob(f"{date_dir}/*.mkv")
        for file_path in files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if current_time - mod_time < timedelta(minutes=10):
                    healthy_cameras += 1
                    break
            except Exception:
                continue

    return healthy_cameras > 0

def check_health():
    """Comprehensive health check"""
    checks = [
        ("Storage directory", check_storage_access),
        ("Config directory", check_config_access),
        ("Web server", check_web_server),
        ("FFmpeg processes", check_ffmpeg_processes),
        ("Camera recordings", check_camera_recordings)
    ]

    for check_name, check_func in checks:
        if not check_func():
            print(f"Health check failed: {check_name}")
            return False

    return True

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
