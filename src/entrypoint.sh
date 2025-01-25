#!/bin/sh
set -eo pipefail

echo "#####################################################"
echo "######## OneNVR - One Network Video Recorder ########"
echo "#####################################################"
echo "Performing initial checks..."
# Get Camera IPs from RTSP URLs using Python
CAMERA_IPS=$(python <<EOF
import yaml, os, re

try:
    with open('/config/config.yaml') as f:
        config = yaml.safe_load(f)

    ips = []
    for cam in config.get('cameras', []):
        # Extract IP from RTSP URL format: rtsp://user:pass@IP:port/path
        match = re.search(r'@([\d\.]+)(:\d+)?/', cam['rtsp_url'])
        if match:
            ips.append(match.group(1))
        else:
            print(f"Warning: Could not extract IP from RTSP URL: {cam['rtsp_url']}", file=os.sys.stderr)

    print(' '.join(ips))
except Exception as e:
    print(f"CONFIG ERROR: {str(e)}", file=os.sys.stderr)
    exit(1)
EOF
)

# Check if any IPs were found
if [ -z "$CAMERA_IPS" ]; then
  echo "ERROR: No valid camera IPs found in RTSP URLs"
  exit 1
fi

echo "Detected camera IPs:"
for ip in $CAMERA_IPS; do
  echo " - $ip"
done

# Ping check function
check_ping() {
  if ping -c 1 -W 2 "$1" >/dev/null 2>&1; then
    return 0
  else
    echo "Camera unreachable: $1" >&2
    return 1
  fi
}

# Wait for at least one camera to respond
echo "Checking camera connectivity..."
ANY_ALIVE=false
while true; do
  for ip in $CAMERA_IPS; do
    if check_ping "$ip"; then
      ANY_ALIVE=true
      break
    fi
  done

  if [ "$ANY_ALIVE" = true ]; then
    echo "At least one camera is reachable - starting OneNVR"
    break
  else
    echo "All cameras unreachable - retrying in 5 seconds..."
    sleep 5
  fi
done

# Start the application
exec python /app/main.py
