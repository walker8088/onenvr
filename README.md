# OneNVR - One Network Video Recorder

[![Repo](https://img.shields.io/badge/Docker-Repo-007EC6?labelColor-555555&color-007EC6&logo=docker&logoColor=fff&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Version](https://img.shields.io/docker/v/cyb3rdoc/onenvr/latest?labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Size](https://img.shields.io/docker/image-size/cyb3rdoc/onenvr/latest?sort=semver&labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Pulls](https://img.shields.io/docker/pulls/cyb3rdoc/onenvr?labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)

This is a simple and lightweight Network Video Recorder (NVR) that is designed to run on cheap hardware, such as a Raspberry Pi with a hard drive. 24/7 video streams from network cameras are saved. Recorded files can be browsed through native web interface.

![Web Interface](/images/web-interface.png)

The project is deliberately bare-bones, configuration is done through `config.yaml` file and deployed using docker containerization.

The camera video streams are saved in 5 minute files (to prevent long periods of video loss should a file become corrupted). At 02:00 UTC, the video files for the previous day are concatenated into a single 24 hour file, and the 5 minute video files are deleted. The concatenation is performed in a way to prevent disk I/O exhaustion and impact on ongoing recording. At 01:00 UTC, the video files older than 7 days are deleted. With local timezone environment variable, the concatenation and deletion tasks will be performed at local time 02:00 and 01:00 respectively. Period of retention, concatenation and deletion times can be configured with `config.yaml` file.

`ffmpeg` is used to connect to the camera streams and save the video feeds. Recording will restart automatically in case of unexpected interruption.

## Configuration Options
1. Use `TZ=America/New_York` environment variable in `docker run` command or `docker-compose.yml` file to have filenames in local timezone of New York.
2. The length of video segments from live streams can be configured by updating `interval: 300` to desired value in seconds (minimum 60) in `config.yaml` file. (Optional)
3. Any codec supported by `ffmpeg` can be used (E.g., libx264) instead of default (and recommended) `codec: copy` however this will depend on hardware capabilities and increase processing strain for system.
4. Set retention period of video files by updating `retention_days: 7` to your desired days in `config.yaml` file. (Optional)
5. Disable concatenation of short video clips to single video file by setting `concatenation: false` in `config.yaml` file. (Optional)
6. Time to run concatenation can be set by updating `concatenation_time: "02:00"` to desired time. (Optional)
7. Time to run deletion of old recordings can be set by updating `deletion_time: "01:00"` to desired time. (Optional)
8. For password protected RTSP camera streams, you need pass the argument in RTSP URL configuration. The URL might vary based on your camera. E.g., `rtsp://user:password@camera-ip/live/stream_01`
9. Logs can be accessed in native docker logs with command `docker logs onenvr`. For detailed logs, use docker environment variable `DEBUG=true` in `docker run` command or `docker-compose.yml` file.

## User authentication for web interface
1. During first use of web interface, you need to set username and password to access the web interface.
2. Only a server administrator with SSH or direct access to OneNVR mountpoints can reset the password using `Forgot Password` option.
3. Use password reset key stored at `/config` mountpoint to set a new password.

![Web Interface](/images/web-login.png)

## Build image using Dockerfile

Clone the repo to build your own image.

```
TIMESTAMP="$(date '+%Y%m%d-%H%M')"

docker build -t "${USER?}/onenvr:${TIMESTAMP}" .
```

Run onenvr docker container:
```
docker run -d --name onenvr -p 80:5000 -v /path/to/onenvr/config:/config -v /path/to/onenvr/storage:/storage your_username/onenvr:YYYYMMDD-HHMM
```

Mount following volumes to update camera settings and access or backup stored video files.
1. /config - For NVR configuration
2. /storage - For recorded videos

## Using docker-compose.yml

You can also use prebuilt image cyb3rdoc/onenvr:latest with docker-compose.yml.
```
services:
  onenvr:
    container_name: onenvr
    hostname: onenvr
    image: cyb3rdoc/onenvr:latest
    ports:
      - "80:5000"
    environment:
      - TZ=America/New_York
      - DEBUG=false
    volumes:
      - /path/to/onenvr/config:/config
      - /path/to/onenvr/storage:/storage
    restart: unless-stopped

```

## NVR Logs
Logs can be accessed with `docker logs onenvr`. For detailed logs, use docker environment variable `DEBUG=true` in `docker run` command or `docker-compose.yml` file.
