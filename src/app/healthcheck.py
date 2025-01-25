import os
import glob
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta

def check_health():
    # Check 1: Verify storage directory exists and is writable
    if not os.path.exists('/storage') or not os.access('/storage', os.W_OK):
        print("Storage directory not accessible")
        return False

    # Check 2: Verify config directory exists and is readable
    if not os.path.exists('/config') or not os.access('/config', os.R_OK):
        print("Config directory not accessible")
        return False

    # Check 3: # Check for web server connection and response
    try:
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as response:
            if response.getcode() != 200:
                print(f"Web server returned unexpected status: {response.getcode()}")
                return False
    except urllib.error.URLError as e:
        print(f"Web server connection failed: {str(e.reason)}")
        return False

    # Check 4: Check for recent recordings in the last 2 minutes
    now = datetime.now()
    recent_files_found = False

    for camera_dir in glob.glob('/storage/*/raw'):
        files = glob.glob(f"{camera_dir}/*.mkv")
        for f in files:
            mod_time = datetime.fromtimestamp(os.path.getmtime(f))
            if now - mod_time < timedelta(minutes=2):
                recent_files_found = True
                break
        if recent_files_found:
            break

    if not recent_files_found:
        print("No recent recordings found")
        return False

    return True

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
