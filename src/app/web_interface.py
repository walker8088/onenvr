import os
import logging
from datetime import datetime
from flask import Flask, send_from_directory, render_template_string, abort

logger = logging.getLogger(__name__)

HTML_TEMPLATES = {
    'camera_list': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OneNVR - Cameras</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f0f2f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                h1 { color: #1a73e8; margin-bottom: 25px; }
                ul { list-style: none; padding: 0; margin: 0; }
                li { margin: 10px 0; padding: 12px; background: #f8f9fa; border-radius: 4px; transition: background 0.2s; }
                li:hover { background: #e9ecef; }
                a { color: #1a73e8; text-decoration: none; font-weight: 500; }
                a:hover { text-decoration: underline; }
                .empty-message { text-align: center; color: #666; padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Cameras</h1>
                {% if cameras %}
                <ul>
                    {% for camera in cameras %}
                    <li><a href="/{{ camera }}/">{{ camera }}</a></li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-message">No cameras configured yet</div>
                {% endif %}
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
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f0f2f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .breadcrumb { color: #666; margin-bottom: 20px; font-size: 0.95em; }
                .breadcrumb a { color: #1a73e8; text-decoration: none; }
                .breadcrumb a:hover { text-decoration: underline; }
                h1 { color: #1a73e8; margin-bottom: 25px; }
                ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
                li { padding: 12px; background: #f8f9fa; border-radius: 4px; text-align: center; transition: background 0.2s; }
                li:hover { background: #e9ecef; }
                a { color: #1a73e8; text-decoration: none; font-weight: 500; }
                a:hover { text-decoration: underline; }
                .empty-message { text-align: center; color: #666; padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb">
                    <a href="/">Cameras</a> &gt;
                    {{ camera }}
                </div>

                <h1>{{ camera }} - Dates</h1>
                {% if dates %}
                <ul>
                    {% for date in dates %}
                    <li><a href="/{{ camera }}/{{ date }}/">{{ date }}</a></li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-message">No recordings available yet</div>
                {% endif %}
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
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f0f2f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .breadcrumb { color: #666; margin-bottom: 20px; font-size: 0.95em; }
                .breadcrumb a { color: #1a73e8; text-decoration: none; }
                .breadcrumb a:hover { text-decoration: underline; }
                h1 { color: #1a73e8; margin-bottom: 25px; }
                .video-grid { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
                .video-item { padding: 20px; background: #f8f9fa; border-radius: 8px; transition: all 0.2s ease; border: 1px solid #e9ecef; }
                .video-item:hover { background: #e9ecef; transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                .video-link { color: #1a73e8; text-decoration: none; display: block; }
                .video-title {font-weight: 600; font-size: 1.1em; margin-bottom: 8px; color: #2c3e50; }
                .timestamp { color: #666; font-size: 0.9em; margin-bottom: 8px; }
                .filename { color: #888; font-size: 0.8em; word-break: break-all; font-family: monospace; background: #fff; padding: 4px; border-radius: 4px; }
                .empty-message {  text-align: center;  color: #666;  padding: 40px; background: #f8f9fa; border-radius: 8px; }
                .video-icon { display: inline-block; width: 24px; height: 24px; margin-right: 8px; vertical-align: middle; }
                .meta-info { display: flex; align-items: center; margin-bottom: 8px; }
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
                {% if videos %}
                <ul class="video-grid">
                    {% for video in videos %}
                    <li class="video-item">
                        <a href="/{{ camera }}/{{ date }}/{{ video }}" class="video-link">
                            <div class="meta-info">
                                <svg class="video-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                <div class="video-title">Recording {{ loop.index }}</div>
                            </div>
                            <div class="timestamp">
                                {% set time = video.split('_')[1].split('.')[0].replace('-', ':') %}
                                {{ time }}
                            </div>
                            <div class="filename">{{ video }}</div>
                        </a>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-message">No recordings available for this date yet</div>
                {% endif %}
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
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f0f2f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .breadcrumb { color: #666; margin-bottom: 20px; font-size: 0.95em; }
                .breadcrumb a { color: #1a73e8; text-decoration: none; }
                .breadcrumb a:hover { text-decoration: underline; }
                h1 { color: #1a73e8; margin-bottom: 25px; }
                .back-link { display: inline-block; margin-bottom: 20px; color: #1a73e8; text-decoration: none; font-weight: 500; }
                .back-link:hover { text-decoration: underline; }
                .video-container { margin-top: 20px; display: flex; justify-content: center; }
                video { width: 100%; max-width: 800px; border-radius: 4px; background: black; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb">
                    <a href="/">Cameras</a> &gt;
                    <a href="/{{ camera }}/">{{ camera }}</a> &gt;
                    <a href="/{{ camera }}/{{ date }}/">{{ date }}</a> &gt;
                    {{ video }}
                </div>

                <a href="/{{ camera }}/{{ date }}/" class="back-link">&larr; Back to list</a>

                <h1>{{ video }}</h1>
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
