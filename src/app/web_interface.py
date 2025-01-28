from datetime import datetime
import os
import logging
from flask import Flask, send_from_directory, render_template_string, abort

logger = logging.getLogger(__name__)

HTML_TEMPLATES = {
    'camera_list': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OneNVR - Cameras</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f0f2f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #1a73e8;
                    margin-bottom: 25px;
                }
                ul {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }
                li {
                    margin: 10px 0;
                    padding: 12px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                li:hover {
                    background: #e9ecef;
                }
                a {
                    color: #1a73e8;
                    text-decoration: none;
                    font-weight: 500;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Cameras</h1>
                <ul>
                    {% for camera in cameras %}
                    <li><a href="/{{ camera }}/">{{ camera }}</a></li>
                    {% endfor %}
                </ul>
            </div>
        </body>
        </html>
    ''',

    'date_list': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ camera }} - Dates</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f0f2f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .breadcrumb {
                    color: #666;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                }
                .breadcrumb a {
                    color: #1a73e8;
                    text-decoration: none;
                }
                .breadcrumb a:hover {
                    text-decoration: underline;
                }
                h1 {
                    color: #1a73e8;
                    margin-bottom: 25px;
                }
                ul {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                    gap: 10px;
                }
                li {
                    padding: 12px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    text-align: center;
                    transition: background 0.2s;
                }
                li:hover {
                    background: #e9ecef;
                }
                a {
                    color: #1a73e8;
                    text-decoration: none;
                    font-weight: 500;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb">
                    <a href="/">Cameras</a> &gt;
                    {{ camera }}
                </div>

                <h1>{{ camera }} - Dates</h1>
                <ul>
                    {% for date in dates %}
                    <li><a href="/{{ camera }}/{{ date }}/">{{ date }}</a></li>
                    {% endfor %}
                </ul>
            </div>
        </body>
        </html>
    ''',

    'video_list': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ camera }} - {{ date }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f0f2f5;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .breadcrumb {
                    color: #666;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                }
                .breadcrumb a {
                    color: #1a73e8;
                    text-decoration: none;
                }
                .breadcrumb a:hover {
                    text-decoration: underline;
                }
                h1 {
                    color: #1a73e8;
                    margin-bottom: 25px;
                }
                .video-grid {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                    gap: 15px;
                }
                .video-item {
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    transition: all 0.2s ease;
                    text-align: center;
                }
                .video-item:hover {
                    background: #e9ecef;
                    transform: translateY(-2px);
                }
                .video-link {
                    color: #1a73e8;
                    text-decoration: none;
                    display: block;
                }
                .timecode {
                    color: #666;
                    font-size: 0.85em;
                    margin-top: 8px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb">
                    <a href="/">Cameras</a> &gt;
                    <a href="/{{ camera }}/">{{ camera }}</a> &gt;
                    {{ date }}
                </div>

                <h1>{{ camera }} - {{ date }}</h1>
                <ul class="video-grid">
                    {% for video in videos %}
                    <li class="video-item">
                        <a href="/{{ camera }}/{{ date }}/{{ video }}" class="video-link">
                            <div style="font-weight: 500;">{{ video.split('_')[1].split('.')[0]|replace('-', ':') }}</div>
                            <div class="timecode">MKV File</div>
                        </a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </body>
        </html>
    ''',

    'video_player': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ camera }} - {{ date }} - {{ video }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f0f2f5;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .breadcrumb {
                    color: #666;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                }
                .breadcrumb a {
                    color: #1a73e8;
                    text-decoration: none;
                }
                .breadcrumb a:hover {
                    text-decoration: underline;
                }
                .back-link {
                    display: inline-block;
                    margin-bottom: 20px;
                    color: #1a73e8;
                    text-decoration: none;
                }
                .back-link:hover {
                    text-decoration: underline;
                }
                .video-container {
                    margin-top: 20px;
                }
                video {
                    width: 100%;
                    max-width: 800px;
                    border-radius: 4px;
                    background: black;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb">
                    <a href="/">Cameras</a> &gt;
                    <a href="/{{ camera }}/">{{ camera }}</a> &gt;
                    <a href="/{{ camera }}/{{ date }}/">{{ date }}</a> &gt;
                    {{ video.split('_')[1].split('.')[0]|replace('-', ':') }}
                </div>

                <a href="/{{ camera }}/{{ date }}/" class="back-link">&larr; Back to list</a>

                <div class="video-container">
                    <video controls preload="metadata">
                        <source src="/video/{{ camera }}/{{ date }}/{{ video }}">
                        Your browser does not support this video format.
                    </video>
                </div>
            </div>
        </body>
        </html>
    '''
}

def create_web_server():
    app = Flask(__name__)
    base_storage = "/storage"

    # Suppress Flask internal logs and development server warning
    app.logger.disabled = True
    app.env = 'production'
    app.config['PROPAGATE_EXCEPTIONS'] = True

    def get_safe_path(*parts):
        sanitized = os.path.normpath(os.path.join(*parts)).lstrip('/')
        if '..' in sanitized or not sanitized.startswith('storage/'):
            abort(404)
        return os.path.join('/', sanitized)

    @app.route('/')
    def root():
        cameras = [name for name in os.listdir(base_storage)
                 if os.path.isdir(os.path.join(base_storage, name))]
        return render_template_string(HTML_TEMPLATES['camera_list'], cameras=cameras)

    @app.route('/<camera>/')
    def camera_dates(camera):
        path = get_safe_path(base_storage, camera)
        all_items = os.listdir(path)
        # Filter and sort dates
        dates = sorted(
            [d for d in all_items
             if os.path.isdir(os.path.join(path, d)) and d != 'raw'],
            key=lambda x: datetime.strptime(x, '%Y-%m-%d'),
            reverse=True
        )
        return render_template_string(HTML_TEMPLATES['date_list'], camera=camera, dates=dates)

    @app.route('/<camera>/<date>/')
    def date_videos(camera, date):
        path = get_safe_path(base_storage, camera, date)
        videos = sorted(
            [v for v in os.listdir(path) if v.endswith('.mkv')],
            key=lambda x: x.split('.')[0],
            reverse=False
        )
        return render_template_string(HTML_TEMPLATES['video_list'],
                                    camera=camera, date=date, videos=videos)

    @app.route('/<camera>/<date>/<video>')
    def play_video(camera, date, video):
        # Verify path validity
        path = get_safe_path(base_storage, camera, date, video)

        if not os.path.isfile(path):
            abort(404)

        return render_template_string(
            HTML_TEMPLATES['video_player'],
            camera=camera,
            date=date,
            video=video
        )

    @app.route('/video/<path:filename>')
    def serve_video(filename):
        safe_path = get_safe_path(base_storage, filename)
        directory = os.path.dirname(safe_path)
        file_name = os.path.basename(safe_path)
        return send_from_directory(directory, file_name)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )

    return app
