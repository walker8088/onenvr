# OneNVR - One Network Video Recorder for All Your Cameras

[![Repo](https://img.shields.io/badge/Docker-Repo-007EC6?labelColor-555555&color-007EC6&logo=docker&logoColor=fff&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Version](https://img.shields.io/docker/v/cyb3rdoc/eznvr/latest?labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Size](https://img.shields.io/docker/image-size/cyb3rdoc/eznvr/latest?sort=semver&labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)
[![Pulls](https://img.shields.io/docker/pulls/cyb3rdoc/eznvr?labelColor-555555&color-007EC6&style=flat-square)](https://hub.docker.com/r/cyb3rdoc/onenvr)

This is a simple and lightweight Network Video Recorder (NVR) that is designed to run on cheap hardware, such as a Raspberry Pi with a hard drive. 24/7 video streams from network cameras are saved. Recorded files can be browsed using [filebrowser](https://github.com/filebrowser/filebrowser).

The project is deliberately bare-bones, configuration is done through `config.yaml` file and deployed using docker containerization.

The camera video streams are saved in 5 minute files (to prevent long periods of video loss should a file become corrupted). At 01:00 UTC, the video files for the previous day are concatenated into a single 24 hour file, and the 5 minute video files are deleted. At 02:00 UTC, the video files older than 7 days are deleted. Period of retention can be changed with `config.yaml` file.

`ffmpeg` is used to connect to the camera streams and save the video feeds. Recording will restart automatically in case of unexpected interruption.

## Configuration Options
1. Use `TZ: Europe/London` environment variable to have filenames in local timezone of London.
2. Set retention period of video files by updating `retention_days: 7` to your desired days in `config.yaml` file. (Optional)
3. Disable concatenation of short video clips to single video file by setting `concatenation: false` in `config.yaml` file. (Optional)
4. Time to run concatenation can be set by updating `concatenation_time: "01:00"` to desired time. (Optional)
5. Time to run deletion of old recordings can be set by updating `deletion_time: "02:00"` to desired time. (Optional)
5. For password protected RTSP streams, you need pass the argument in RTSP URL configuration based on your camera. E.g., rtsp://user:password@camera-ip/live/stream_01
7. Logs can be accessed in native docker logs.

## Build image using Dockerfile

Clone the repo to build your own image.

```
TIMESTAMP="$(date '+%Y%m%d-%H%M')"

docker build -t "${USER?}/onenvr:${TIMESTAMP}" .
```

Run onenvr docker container:
```
docker run -d --name onenvr -v /path/to/onenvr/config:/config -v /path/to/onenvr/storage:/storage your_username/onenvr:YYYYMMDD-HHMM
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
    volumes:
      - /path/to/onenvr/config:/config
      - /path/to/onenvr/storage:/storage
    restart: unless-stopped

```

## NVR Logs
Logs can be accessed with `docker logs onenvr`. For detailed logs, use docker environment variable `DEBUG=true` in docker command or docker-compose.yml file.
