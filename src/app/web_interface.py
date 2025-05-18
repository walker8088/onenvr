import os
import logging
import hashlib
import secrets
from datetime import datetime
from flask import Flask, send_from_directory, render_template_string, abort, request, redirect, url_for, session, flash
from functools import wraps

logger = logging.getLogger(__name__)

HTML_TEMPLATES = {
    'login': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OneNVR - Login</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .login-container { width: 350px; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                h1 { color: #1a73e8; margin-bottom: 25px; text-align: center; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 6px; color: #555; font-weight: 500; }
                input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 15px; }
                input[type="submit"] { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; transition: background 0.2s; }
                input[type="submit"]:hover { background: #0f62fe; }
                .message { padding: 10px; background: #f2dede; color: #a94442; border-radius: 4px; margin-bottom: 15px; text-align: center; }
                .success-message { padding: 10px; background: #d4edda; color: #155724; border-radius: 4px; margin-bottom: 15px; text-align: center; }
                .setup-message { text-align: center; margin-bottom: 20px; color: #666; }
                .forgot-password { display: block; text-align: center; margin-top: 15px; color: #1a73e8; text-decoration: none; font-size: 0.9em; }
                .forgot-password:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>OneNVR</h1>

                {% if setup_required %}
                <div class="setup-message">First-time setup: Create your login credentials</div>
                {% endif %}

                {% if reset_mode %}
                <div class="setup-message">Reset your password using the reset key</div>
                {% endif %}

                {% if error %}
                <div class="message">{{ error }}</div>
                {% endif %}

                {% if success %}
                <div class="success-message">{{ success }}</div>
                {% endif %}

                <form method="post">
                    {% if reset_key_form %}
                    <div class="form-group">
                        <label for="reset_key">Reset Key</label>
                        <input type="text" id="reset_key" name="reset_key" required>
                    </div>
                    <div class="form-group">
                        <label for="new_password">New Password</label>
                        <input type="password" id="new_password" name="new_password" required>
                    </div>
                    <div class="form-group">
                        <label for="confirm_new_password">Confirm New Password</label>
                        <input type="password" id="confirm_new_password" name="confirm_new_password" required>
                    </div>
                    <input type="submit" value="Reset Password">
                    <a href="/login" class="forgot-password">Back to Login</a>
                    {% elif reset_mode %}
                    <div class="setup-message">A reset key has been generated and saved in the application directory.<br>Check the file: <strong>password_reset.key</strong></div>
                    <div class="form-group">
                        <a href="/reset_password" class="forgot-password">I have the reset key</a>
                    </div>
                    <a href="/login" class="forgot-password">Back to Login</a>
                    {% else %}
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    {% if setup_required %}
                    <div class="form-group">
                        <label for="confirm_password">Confirm Password</label>
                        <input type="password" id="confirm_password" name="confirm_password" required>
                    </div>
                    {% endif %}
                    <input type="submit" value="{% if setup_required %}Create Account{% else %}Login{% endif %}">
                    {% if not setup_required %}
                    <a href="/forgot_password" class="forgot-password">Forgot Password?</a>
                    {% endif %}
                    {% endif %}
                </form>
            </div>
        </body>
        </html>
    ''',

    'camera_list': '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OneNVR - Cameras</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f0f2f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .logout { color: #666; text-decoration: none; font-size: 0.9em; }
                .logout:hover { text-decoration: underline; }
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
                <div class="header">
                    <h1>Cameras</h1>
                    <a href="/logout" class="logout">Logout</a>
                </div>
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
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .logout { color: #666; text-decoration: none; font-size: 0.9em; }
                .logout:hover { text-decoration: underline; }
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
                <div class="header">
                    <div class="breadcrumb">
                        <a href="/">Cameras</a> &gt;
                        {{ camera }}
                    </div>
                    <a href="/logout" class="logout">Logout</a>
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
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .logout { color: #666; text-decoration: none; font-size: 0.9em; }
                .logout:hover { text-decoration: underline; }
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
                <div class="header">
                    <div class="breadcrumb">
                        <a href="/">Cameras</a> &gt;
                        <a href="/{{ camera }}/">{{ camera }}</a> &gt;
                        {{ date }}
                    </div>
                    <a href="/logout" class="logout">Logout</a>
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
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .logout { color: #666; text-decoration: none; font-size: 0.9em; }
                .logout:hover { text-decoration: underline; }
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
                <div class="header">
                    <div class="breadcrumb">
                        <a href="/">Cameras</a> &gt;
                        <a href="/{{ camera }}/">{{ camera }}</a> &gt;
                        <a href="/{{ camera }}/{{ date }}/">{{ date }}</a> &gt;
                        {{ video }}
                    </div>
                    <a href="/logout" class="logout">Logout</a>
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
    auth_file = os.path.join(base_storage, 'auth.dat')
    reset_key_file = os.path.join(os.path.dirname(auth_file), 'password_reset.key')

    # Set secret key for session
    app.secret_key = secrets.token_hex(16)

    # Suppress Flask internal logs and development server warning
    app.logger.disabled = True
    app.env = 'production'
    app.config['PROPAGATE_EXCEPTIONS'] = True

    def get_safe_path(*parts):
        sanitized = os.path.normpath(os.path.join(*parts)).lstrip('/')
        if '..' in sanitized or not sanitized.startswith('storage/'):
            abort(404)
        return os.path.join('/', sanitized)

    def is_setup_required():
        return not os.path.exists(auth_file)

    def hash_password(password):
        salt = secrets.token_hex(8)
        h = hashlib.sha256()
        h.update((password + salt).encode('utf-8'))
        return f"{salt}:{h.hexdigest()}"

    def verify_password(stored_hash, password):
        salt, hash_value = stored_hash.split(':')
        h = hashlib.sha256()
        h.update((password + salt).encode('utf-8'))
        return h.hexdigest() == hash_value

    def create_user(username, password):
        with open(auth_file, 'w') as f:
            f.write(f"{username}:{hash_password(password)}")

    def check_auth(username, password):
        try:
            with open(auth_file, 'r') as f:
                stored_user, stored_hash = f.read().strip().split(':', 1)
                return username == stored_user and verify_password(stored_hash, password)
        except (FileNotFoundError, ValueError):
            return False

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'authenticated' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/forgot_password')
    def forgot_password():
        # Generate a random reset key
        reset_key = secrets.token_hex(16)

        # Save the reset key to a file
        with open(reset_key_file, 'w') as f:
            f.write(reset_key)

        return render_template_string(HTML_TEMPLATES['login'], reset_mode=True, error=None, setup_required=False)

    @app.route('/reset_password', methods=['GET', 'POST'])
    def reset_password():
        error = None
        success = None

        if not os.path.exists(auth_file):
            return redirect(url_for('login'))

        if request.method == 'POST':
            reset_key = request.form['reset_key']
            new_password = request.form['new_password']
            confirm_new_password = request.form['confirm_new_password']

            # Verify the reset key
            try:
                with open(reset_key_file, 'r') as f:
                    stored_key = f.read().strip()

                if reset_key != stored_key:
                    error = "Invalid reset key"
                elif new_password != confirm_new_password:
                    error = "Passwords do not match"
                elif len(new_password) < 6:
                    error = "Password must be at least 6 characters"
                else:
                    # Read the current username
                    with open(auth_file, 'r') as f:
                        current_username = f.read().strip().split(':', 1)[0]

                    # Update the password
                    create_user(current_username, new_password)

                    # Remove the reset key file
                    if os.path.exists(reset_key_file):
                        os.remove(reset_key_file)

                    success = "Password has been reset successfully. You can now login."
            except FileNotFoundError:
                error = "Reset key not found. Please request a new password reset."

        return render_template_string(HTML_TEMPLATES['login'], reset_key_form=True, error=error, success=success, setup_required=False)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        setup_mode = is_setup_required()

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            if setup_mode:
                confirm_password = request.form['confirm_password']
                if password != confirm_password:
                    error = "Passwords do not match"
                elif len(password) < 6:
                    error = "Password must be at least 6 characters"
                else:
                    # Create the user
                    os.makedirs(os.path.dirname(auth_file), exist_ok=True)
                    create_user(username, password)
                    session['authenticated'] = True
                    return redirect(url_for('root'))
            else:
                if check_auth(username, password):
                    session['authenticated'] = True
                    return redirect(url_for('root'))
                else:
                    error = "Invalid username or password"

        return render_template_string(HTML_TEMPLATES['login'], error=error, setup_required=setup_mode)

    @app.route('/logout')
    def logout():
        session.pop('authenticated', None)
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def root():
        cameras = [name for name in os.listdir(base_storage)
                 if os.path.isdir(os.path.join(base_storage, name)) and name != 'auth.dat']
        return render_template_string(HTML_TEMPLATES['camera_list'], cameras=cameras)

    @app.route('/<camera>/')
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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

    # Redirect all requests to login if not authenticated
    @app.before_request
    def before_request():
        # Skip authentication for login page, password reset and static files
        if request.endpoint in ['login', 'forgot_password', 'reset_password', 'favicon', 'static']:
            return

        if 'authenticated' not in session:
            return redirect(url_for('login'))

    return app
