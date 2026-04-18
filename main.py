import os
import json
import time
import base64
import hashlib
import secrets
import re
from datetime import datetime
from functools import wraps
import pytz
from flask import (
    Flask, render_template, jsonify, request,
    send_from_directory, session, redirect
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import werkzeug.utils
import cloudinary
import cloudinary.uploader

load_dotenv()


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL   = 'gemini-2.5-flash' # text/vision analysis model

# Encryption key for API keys stored in Google Sheets
# Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY = os.getenv('FERNET_KEY', '')
_fernet = Fernet(FERNET_KEY.encode()) if FERNET_KEY else None

# ─────────────────────────────────────────────────────────────
# CLOUDINARY CONFIG  (persistent image hosting)
# Keys are set ONLY via Render environment variables — never hardcoded.
# ─────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    api_key    = os.getenv('CLOUDINARY_API_KEY', ''),
    api_secret = os.getenv('CLOUDINARY_API_SECRET', ''),
    secure     = True
)

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Secure Session Configurations (Updated for Cross-Site Embed support)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None' # Required for Google Sites iframe support

GOOGLE_SHEET_ID   = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')

# Admin credentials — MUST be set as 'ADMIN_PASSWORD' in Render environment variables.
# No default is provided. If not set, admin login is permanently disabled.
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

INDIA_TZ = pytz.timezone('Asia/Kolkata')

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ─────────────────────────────────────────────────────────────
# SECURITY: DDOS/Quota Rate Limiting & HTTP Shields
# ─────────────────────────────────────────────────────────────
from collections import defaultdict
import time

API_RATE_LIMITER = defaultdict(list)

@app.before_request
def check_rate_limit():
    """Prevents API brute forcing, DDoS, and AI API quota draining per IP."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not request.path.startswith('/api/'):
        return
        
    now = time.time()
    API_RATE_LIMITER[ip] = [t for t in API_RATE_LIMITER[ip] if now - t < 60]
    
    # Separate per-endpoint counter for generate-image so page-load API calls
    # don't consume the image-generation budget.
    gen_key = ip + '::generate-image'
    if request.path == '/api/v1/generate-image':
        API_RATE_LIMITER[gen_key] = [t for t in API_RATE_LIMITER[gen_key] if now - t < 60]
        if len(API_RATE_LIMITER[gen_key]) >= 5:
            return jsonify({
                'status': 'error',
                'message': 'Security Block: Too many image generation requests. Please wait a minute.'
            }), 429
        API_RATE_LIMITER[gen_key].append(now)
        return  # skip the general counter for this endpoint

    # General API rate limit: 60 requests/min per IP
    limit = 60
        
    if len(API_RATE_LIMITER[ip]) >= limit:
        return jsonify({
            'status': 'error', 
            'message': 'Security Block: Too many requests from this IP. Please slow down.'
        }), 429
        
    API_RATE_LIMITER[ip].append(now)

@app.after_request
def apply_security_headers(response):
    """Applies strict HTTP headers and enables CORS for Google Sites embeds."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Only apply CORS to API endpoints, never to sitemap/ads.txt/robots.txt
    if request.path.startswith('/api/'):
        origin = request.headers.get('Origin')
        if origin and ('.googleusercontent.com' in origin or 'sites.google.com' in origin or 'render.com' in origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Explicit preflight handler for API calls."""
    response = jsonify({'status': 'ok'})
    origin = request.headers.get('Origin')
    if origin and ('.googleusercontent.com' in origin or 'sites.google.com' in origin or 'render.com' in origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return response

# ─────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────
cache = {
    'prompts':    None,
    'analytics':  None,
    'comments':   None,
    'last_update': 0
}
CACHE_TIMEOUT = 60  # 1 minute (fast updates for new prompts)


def invalidate_cache():
    cache['last_update'] = 0


# ─────────────────────────────────────────────────────────────
# GOOGLE SHEETS HELPERS
# ─────────────────────────────────────────────────────────────
def get_google_client():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    if GOOGLE_CREDENTIALS:
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    return gspread.authorize(creds)


def fetch_data():
    now = time.time()
    if cache['prompts'] and (now - cache['last_update'] < CACHE_TIMEOUT):
        return cache
    try:
        client = get_google_client()
        ss = client.open_by_key(GOOGLE_SHEET_ID)

        cache['prompts'] = ss.sheet1.get_all_records()

        try:
            cache['analytics'] = ss.worksheet('Analytics').get_all_records()
        except Exception:
            cache['analytics'] = []

        try:
            cache['comments'] = ss.worksheet('Comments').get_all_records()
        except Exception:
            cache['comments'] = []

        cache['last_update'] = now
    except Exception as e:
        print(f'fetch_data error: {e}')
    return cache


def ts():
    return datetime.now(INDIA_TZ).strftime('%Y-%m-%d %H:%M:%S')


# ─────────────────────────────────────────────────────────────
# USER AUTH HELPERS
# ─────────────────────────────────────────────────────────────
def _hash_password(password):
    """SHA-256 hash with a per-password salt (stored together)."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(stored_hash, password):
    if ':' not in stored_hash:
        return False
    salt, h = stored_hash.split(':', 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


def _encrypt_api_key(api_key):
    """Encrypt an API key using Fernet. Falls back to base64 if no FERNET_KEY."""
    if _fernet:
        return _fernet.encrypt(api_key.encode()).decode()
    return base64.b64encode(api_key.encode()).decode()


def _decrypt_api_key(encrypted_key):
    """Decrypt an API key."""
    if not encrypted_key:
        return ''
    if _fernet:
        try:
            return _fernet.decrypt(encrypted_key.encode()).decode()
        except Exception:
            return ''
    try:
        return base64.b64decode(encrypted_key.encode()).decode()
    except Exception:
        return ''


def _get_users_sheet():
    """Get or create the 'Users' worksheet."""
    client = get_google_client()
    ss = client.open_by_key(GOOGLE_SHEET_ID)
    try:
        sheet = ss.worksheet('Users')
    except gspread.exceptions.WorksheetNotFound:
        sheet = ss.add_worksheet(title='Users', rows=10000, cols=6)
        sheet.update('A1:F1', [['Name', 'Email', 'Password Hash', 'API Key (encrypted)', 'Created At', 'Last Login']])
    return sheet


def _find_user_by_email(email):
    """Find user row by email. Returns (row_number, row_dict) or (None, None)."""
    sheet = _get_users_sheet()
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get('Email', '')).strip().lower() == email.strip().lower():
            return i, row
    return None, None


def _get_user_api_key(email):
    """Retrieve and decrypt the API key for the logged-in user."""
    _, user = _find_user_by_email(email)
    if user:
        encrypted = user.get('API Key (encrypted)', '')
        return _decrypt_api_key(encrypted)
    return ''


# ─────────────────────────────────────────────────────────────
# USER AUTH ENDPOINTS
# ─────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def user_register():
    body = request.json or {}
    name = (body.get('name') or '').strip()
    email = (body.get('email') or '').strip().lower()
    password = (body.get('password') or '')
    api_key = (body.get('api_key') or '').strip()

    # Validation
    if not name or len(name) > 100:
        return jsonify({'status': 'error', 'message': 'Name is required (max 100 characters).'}), 400
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'status': 'error', 'message': 'Please enter a valid email address.'}), 400
    if not password or len(password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters.'}), 400
    if not api_key or not api_key.startswith('AIza'):
        return jsonify({'status': 'error', 'message': 'Please enter a valid Gemini API key. It should start with "AIza...". Get one free at https://aistudio.google.com/apikey'}), 400

    try:
        # Check if email already exists
        existing_row, _ = _find_user_by_email(email)
        if existing_row:
            return jsonify({'status': 'error', 'message': 'An account with this email already exists. Please login.'}), 409

        # Create user
        sheet = _get_users_sheet()
        password_hash = _hash_password(password)
        encrypted_key = _encrypt_api_key(api_key)
        sheet.append_row([name, email, password_hash, encrypted_key, ts(), ts()])

        # Auto-login after registration
        session['user_email'] = email
        session['user_name'] = name
        session.permanent = True

        return jsonify({'status': 'success', 'message': 'Account created successfully!', 'user': {'name': name, 'email': email}})
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({'status': 'error', 'message': 'Registration failed. Please try again.'}), 500


@app.route('/api/auth/login', methods=['POST'])
def user_login():
    body = request.json or {}
    email = (body.get('email') or '').strip().lower()
    password = (body.get('password') or '')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required.'}), 400

    try:
        row_num, user = _find_user_by_email(email)
        if not user:
            return jsonify({'status': 'error', 'message': 'No account found with this email.'}), 401

        stored_hash = user.get('Password Hash', '')
        if not _verify_password(stored_hash, password):
            return jsonify({'status': 'error', 'message': 'Incorrect password.'}), 401

        # Update last login
        try:
            sheet = _get_users_sheet()
            headers = sheet.row_values(1)
            last_login_col = headers.index('Last Login') + 1
            sheet.update_cell(row_num, last_login_col, ts())
        except Exception:
            pass

        session['user_email'] = email
        session['user_name'] = user.get('Name', '')
        session.permanent = True

        return jsonify({'status': 'success', 'message': 'Logged in!', 'user': {'name': user.get('Name', ''), 'email': email}})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': 'Login failed. Please try again.'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def user_logout():
    session.pop('user_email', None)
    session.pop('user_name', None)
    return jsonify({'status': 'success', 'message': 'Logged out.'})


@app.route('/api/auth/status')
def user_auth_status():
    email = session.get('user_email')
    if email:
        return jsonify({'logged_in': True, 'user': {'name': session.get('user_name', ''), 'email': email}})
    return jsonify({'logged_in': False})


# ─────────────────────────────────────────────────────────────
# AUTH DECORATOR
# ─────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# PUBLIC ROUTES
# ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')



@app.route('/admin')
def admin_page():
    return render_template('index.html')


# ─────────────────────────────────────────────────────────────
# CONTENT PAGES  (for AdSense / SEO quality)
# ─────────────────────────────────────────────────────────────
@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/blog')
def blog_page():
    return render_template('blog.html')

@app.route('/blog/how-to-write-ai-video-prompts')
def blog_how_to_write():
    return render_template('blog_how_to_write.html')

@app.route('/blog/runway-ml-vs-pika-labs')
def blog_runway_vs_pika():
    return render_template('blog_runway_vs_pika.html')

@app.route('/blog/cinematic-lighting-prompts')
def blog_cinematic_lighting():
    return render_template('blog_cinematic_lighting.html')

@app.route('/blog/ai-video-prompts-for-social-media')
def blog_social_media():
    return render_template('blog_social_media.html')

@app.route('/blog/nature-landscape-prompts')
def blog_nature_landscape():
    return render_template('blog_nature_landscape.html')

@app.route('/blog/scifi-cinematic-prompts')
def blog_scifi():
    return render_template('blog_scifi.html')



# ─────────────────────────────────────────────────────────────
# API — Public Data
# ─────────────────────────────────────────────────────────────
@app.route('/api/v1/prompts')
def get_prompts():
    data = fetch_data()
    return jsonify({
        'prompts':   data['prompts']   or [],
        'analytics': data['analytics'] or [],
        'comments':  data['comments']  or [],
    })


@app.route('/api/v1/interaction', methods=['POST'])
def interaction():
    body      = request.json or {}
    action    = body.get('action')
    prompt_id = body.get('prompt_id', '')

    try:
        client = get_google_client()
        ss     = client.open_by_key(GOOGLE_SHEET_ID)

        if action == 'like':
            sheet = ss.worksheet('Analytics')
            sheet.append_row([ts(), prompt_id, 'like', 'N/A', '', 'success'])
            invalidate_cache()
            return jsonify({'status': 'success'})

        elif action == 'comment':
            name    = body.get('name', 'Anonymous')[:200]
            comment = body.get('comment', '').strip()
            if not comment:
                return jsonify({'status': 'error', 'message': 'Comment is empty'}), 400
            sheet = ss.worksheet('Comments')
            sheet.append_row([ts(), prompt_id, name, comment[:5000], 'approved', 'N/A'])
            invalidate_cache()
            return jsonify({'status': 'success'})

        return jsonify({'status': 'error', 'message': 'Unknown action'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/analytics', methods=['POST'])
def log_analytics():
    body       = request.json or {}
    event_type = body.get('event_type', 'visit')
    prompt_id  = body.get('prompt_id', 'N/A')
    user_ip    = request.headers.get('X-Forwarded-For', request.remote_addr)

    try:
        client = get_google_client()
        ss     = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            sheet = ss.worksheet('Analytics')
        except Exception:
            sheet = ss.add_worksheet(title='Analytics', rows=10000, cols=6)
            sheet.update('A1:F1', [['Timestamp', 'Prompt ID', 'Event Type',
                                     'User IP', 'Error Message', 'Status']])
        sheet.append_row([ts(), prompt_id, event_type, user_ip, '', 'success'])
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# API — Admin Auth
# ─────────────────────────────────────────────────────────────
@app.route('/api/v1/admin/login', methods=['POST'])
def admin_login():
    # Block login entirely if ADMIN_PASSWORD env var is not configured
    if not ADMIN_PASSWORD:
        return jsonify({'status': 'error', 'message': 'Admin access is not configured on this server.'}), 503

    body     = request.json or {}
    received = body.get('password', '')

    # Client sends SHA-256(password); compare against SHA-256(ADMIN_PASSWORD)
    expected = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    if received and received == expected:
        session.permanent = True
        session['admin_logged_in'] = True
        return jsonify({'status': 'success', 'message': 'Logged in'})
    return jsonify({'status': 'error', 'message': 'Invalid password'}), 401


@app.route('/api/v1/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'status': 'success'})


@app.route('/api/v1/admin/status')
def admin_status():
    return jsonify({'is_admin': bool(session.get('admin_logged_in'))})


# ─────────────────────────────────────────────────────────────
# FEATURE FLAGS
# ─────────────────────────────────────────────────────────────

# Default feature flags — add new features here
DEFAULT_FEATURE_FLAGS = {
    'generate_button': {'enabled': True, 'description': 'Generate AI Image Button'},
}

# In-memory cache of current flags (loaded from Google Sheets)
_feature_flags_cache = None
_feature_flags_last_load = 0
FEATURE_FLAGS_CACHE_TTL = 60  # seconds


def _get_feature_flags_sheet():
    """Get or create the 'FeatureFlags' worksheet."""
    client = get_google_client()
    ss = client.open_by_key(GOOGLE_SHEET_ID)
    try:
        sheet = ss.worksheet('FeatureFlags')
    except gspread.exceptions.WorksheetNotFound:
        sheet = ss.add_worksheet(title='FeatureFlags', rows=100, cols=4)
        sheet.update('A1:D1', [['Flag Name', 'Enabled', 'Description', 'Updated At']])
        # Seed defaults
        for name, meta in DEFAULT_FEATURE_FLAGS.items():
            sheet.append_row([name, 'TRUE', meta['description'], ts()])
    return sheet


def _load_feature_flags():
    """Load feature flags from Google Sheets with in-memory caching."""
    global _feature_flags_cache, _feature_flags_last_load
    now = time.time()
    if _feature_flags_cache is not None and (now - _feature_flags_last_load < FEATURE_FLAGS_CACHE_TTL):
        return _feature_flags_cache

    try:
        sheet = _get_feature_flags_sheet()
        records = sheet.get_all_records()
        flags = {}
        for row in records:
            name = str(row.get('Flag Name', '')).strip()
            if name:
                enabled_val = str(row.get('Enabled', 'TRUE')).strip().upper()
                flags[name] = {
                    'enabled': enabled_val in ('TRUE', '1', 'YES'),
                    'description': row.get('Description', ''),
                }
        # Fill in any defaults that aren't yet in the sheet
        for name, meta in DEFAULT_FEATURE_FLAGS.items():
            if name not in flags:
                flags[name] = {'enabled': meta['enabled'], 'description': meta['description']}
        _feature_flags_cache = flags
        _feature_flags_last_load = now
    except Exception as e:
        print(f'_load_feature_flags error: {e}')
        if _feature_flags_cache is None:
            _feature_flags_cache = {
                name: {'enabled': meta['enabled'], 'description': meta['description']}
                for name, meta in DEFAULT_FEATURE_FLAGS.items()
            }
    return _feature_flags_cache


def _save_feature_flag(flag_name, enabled):
    """Persist a single flag to Google Sheets and bust the cache."""
    global _feature_flags_cache, _feature_flags_last_load
    sheet = _get_feature_flags_sheet()
    records = sheet.get_all_records()
    headers = sheet.row_values(1)

    name_col    = headers.index('Flag Name') + 1
    enabled_col = headers.index('Enabled') + 1
    ts_col      = headers.index('Updated At') + 1

    row_num = None
    for i, row in enumerate(records, start=2):
        if str(row.get('Flag Name', '')).strip() == flag_name:
            row_num = i
            break

    enabled_str = 'TRUE' if enabled else 'FALSE'
    if row_num:
        sheet.update_cell(row_num, enabled_col, enabled_str)
        sheet.update_cell(row_num, ts_col, ts())
    else:
        desc = DEFAULT_FEATURE_FLAGS.get(flag_name, {}).get('description', '')
        sheet.append_row([flag_name, enabled_str, desc, ts()])

    # Update in-memory cache immediately
    if _feature_flags_cache is not None:
        if flag_name in _feature_flags_cache:
            _feature_flags_cache[flag_name]['enabled'] = enabled
        else:
            _feature_flags_cache[flag_name] = {
                'enabled': enabled,
                'description': DEFAULT_FEATURE_FLAGS.get(flag_name, {}).get('description', ''),
            }
    _feature_flags_last_load = time.time()


@app.route('/api/v1/feature-flags')
def get_feature_flags():
    """Public endpoint — returns which features are enabled."""
    flags = _load_feature_flags()
    # Only expose enabled state (not internal metadata)
    return jsonify({name: meta['enabled'] for name, meta in flags.items()})


@app.route('/api/v1/admin/feature-flags', methods=['GET'])
@admin_required
def admin_get_feature_flags():
    """Admin: returns full flag state including descriptions."""
    flags = _load_feature_flags()
    return jsonify(flags)


@app.route('/api/v1/admin/feature-flags', methods=['POST'])
@admin_required
def admin_save_feature_flags():
    """Admin: update one or more feature flags. Body: {flag_name: bool, ...}"""
    body = request.json or {}
    if not isinstance(body, dict):
        return jsonify({'status': 'error', 'message': 'Expected a JSON object'}), 400

    known_flags = set(DEFAULT_FEATURE_FLAGS.keys()) | set((_load_feature_flags() or {}).keys())
    updated = []
    for flag_name, enabled in body.items():
        if flag_name not in known_flags:
            continue  # ignore unknown flags silently
        if not isinstance(enabled, bool):
            continue
        try:
            _save_feature_flag(flag_name, enabled)
            updated.append(flag_name)
        except Exception as e:
            print(f'save_feature_flag({flag_name}) error: {e}')

    return jsonify({'status': 'success', 'updated': updated})


# ─────────────────────────────────────────────────────────────
# API — Admin Prompt CRUD  (protected)
# ─────────────────────────────────────────────────────────────

@app.route('/api/v1/admin/upload-image', methods=['POST'])
@admin_required
def upload_image():
    """Upload an image to Cloudinary and return the permanent URL."""
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    # Validate file type
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400

    try:
        # Upload directly from the file stream — no local disk needed
        result = cloudinary.uploader.upload(
            file,
            folder='video-prompts-gallery',
            resource_type='image',
            overwrite=False,
            unique_filename=True,
        )
        permanent_url = result.get('secure_url', '')
        if not permanent_url:
            raise ValueError('Cloudinary returned no URL')
        return jsonify({'status': 'success', 'url': permanent_url})
    except Exception as e:
        print(f'[Cloudinary upload error] {e}')
        return jsonify({'status': 'error', 'message': f'Upload failed: {str(e)}'}), 500


def _generate_id():
    """Generate a unique prompt ID like PR2104151003."""
    now = datetime.now(INDIA_TZ)
    return f"PR{now.strftime('%y%m%d%H%M%S')}"


@app.route('/api/v1/admin/prompt', methods=['POST'])
@admin_required
def create_prompt():
    """Create a new prompt row in the Google Sheet."""
    body = request.json or {}
    name     = body.get('name', '').strip()
    category = body.get('category', '').strip()
    prompt   = body.get('prompt', '').strip()
    video_id = body.get('video_id', '').strip()
    ai_tool  = body.get('ai_tool', 'Gemini').strip()
    image_url = body.get('image_url', '').strip()

    if not name or not prompt:
        return jsonify({'status': 'error', 'message': 'Name and Prompt are required'}), 400

    try:
        client   = get_google_client()
        ss       = client.open_by_key(GOOGLE_SHEET_ID)
        sheet    = ss.sheet1
        
        # Determine column order dynamically
        headers = sheet.row_values(1)
        
        # Ensure 'Image URL' and 'AI Tool' columns exist dynamically
        added_cols = False
        if 'Image URL' not in headers:
            headers.append('Image URL')
            added_cols = True
        if 'AI Tool' not in headers:
            headers.append('AI Tool')
            added_cols = True
            
        if added_cols:
            sheet.update('A1', [headers])

        # Required columns: Category, Prompt, Prompt Name, Timestamp, Unique ID
        def get_idx(name):
            try: return headers.index(name)
            except: return -1

        cat_idx   = get_idx('Category')
        prompt_idx = get_idx('Prompt')
        name_idx   = get_idx('Prompt Name')
        ts_idx     = get_idx('Timestamp')
        id_idx     = get_idx('Unique ID')
        vid_idx    = get_idx('Video ID')
        tool_idx   = get_idx('AI Tool')
        img_idx    = get_idx('Image URL')

        new_id    = _generate_id()
        timestamp = ts()

        # Build a row of the same length as headers
        row_data = [""] * len(headers)
        if cat_idx != -1:    row_data[cat_idx]    = category
        if prompt_idx != -1: row_data[prompt_idx] = prompt
        if name_idx != -1:   row_data[name_idx]   = name
        if ts_idx != -1:     row_data[ts_idx]     = timestamp
        if id_idx != -1:     row_data[id_idx]     = new_id
        if vid_idx != -1:    row_data[vid_idx]    = video_id
        if tool_idx != -1:   row_data[tool_idx]   = ai_tool
        if img_idx != -1:    row_data[img_idx]    = image_url

        sheet.append_row(row_data)
        invalidate_cache()
        return jsonify({'status': 'success', 'id': new_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/admin/prompt/<prompt_id>', methods=['PUT'])
@admin_required
def update_prompt(prompt_id):
    """Update an existing prompt by Unique ID."""
    body     = request.json or {}
    name     = body.get('name', '').strip()
    category = body.get('category', '').strip()
    prompt   = body.get('prompt', '').strip()
    video_id = body.get('video_id', '').strip()
    ai_tool  = body.get('ai_tool', 'Gemini').strip()
    image_url = body.get('image_url', '').strip()

    if not name or not prompt:
        return jsonify({'status': 'error', 'message': 'Name and Prompt are required'}), 400

    try:
        client = get_google_client()
        ss     = client.open_by_key(GOOGLE_SHEET_ID)
        sheet  = ss.sheet1
        data   = sheet.get_all_records()
        headers = sheet.row_values(1)

        # Ensure dynamic columns exist
        added_cols = False
        if 'Image URL' not in headers:
            headers.append('Image URL')
            added_cols = True
        if 'AI Tool' not in headers:
            headers.append('AI Tool')
            added_cols = True
            
        if added_cols:
            sheet.update('A1', [headers])

        id_col     = headers.index('Unique ID') + 1
        name_col   = headers.index('Prompt Name') + 1
        cat_col    = headers.index('Category') + 1
        prompt_col = headers.index('Prompt') + 1
        vid_col    = (headers.index('Video ID') + 1) if 'Video ID' in headers else None
        tool_col   = (headers.index('AI Tool') + 1) if 'AI Tool' in headers else None
        img_col    = (headers.index('Image URL') + 1) if 'Image URL' in headers else None

        row_num = None
        for i, row in enumerate(data, start=2):
            if row.get('Unique ID') == prompt_id:
                row_num = i
                break

        if row_num is None:
            return jsonify({'status': 'error', 'message': 'Prompt not found'}), 404

        sheet.update_cell(row_num, name_col,   name)
        sheet.update_cell(row_num, cat_col,    category)
        sheet.update_cell(row_num, prompt_col, prompt)
        if vid_col and video_id:
            sheet.update_cell(row_num, vid_col, video_id)
        if tool_col and ai_tool:
            sheet.update_cell(row_num, tool_col, ai_tool)
        if img_col is not None:
            sheet.update_cell(row_num, img_col, image_url)

        invalidate_cache()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# AI IMAGE GENERATION
# ─────────────────────────────────────────────────────────────
@app.route('/api/v1/debug/models')
def list_available_models():
    """Lists Gemini models available to this API key — for diagnostics."""
    import urllib.request, json
    if not GEMINI_API_KEY:
        return jsonify({'error': 'No API key configured'}), 500
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}&pageSize=100"
        with urllib.request.urlopen(urllib.request.Request(url)) as r:
            data = json.loads(r.read().decode())
        models = [{'name': m['name'], 'methods': m.get('supportedGenerationMethods', [])}
                  for m in data.get('models', [])]
        return jsonify({'count': len(models), 'models': models})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/generate-image', methods=['POST'])
def generate_image_api():
    """Generates an image from prompt + optional reference image using Gemini (primary)
    and OpenAI DALL-E 3 (fallback). When a reference image is uploaded the model
    performs image-editing — keeping the subject’s appearance while changing the scene.
    Requires user login — uses the user's own Gemini API key.
    """
    import urllib.request, urllib.error, urllib.parse, json

    # ── AUTH CHECK ─────────────────────────────────────────────
    is_admin = session.get('admin_logged_in')
    user_email = session.get('user_email')

    if not is_admin and not user_email:
        return jsonify({'status': 'error', 'message': 'LOGIN_REQUIRED'}), 401

    # Admin uses the server-level API key; regular users use their own key
    if is_admin:
        user_gemini_key = GEMINI_API_KEY
    else:
        user_gemini_key = _get_user_api_key(user_email)

    if not user_gemini_key:
        return jsonify({'status': 'error', 'message': 'No API key found for your account. Please contact support.'}), 500

    body      = request.json or {}
    prompt    = (body.get('prompt') or '').strip()
    image_b64 = body.get('image_b64', '')

    if not prompt:
        return jsonify({'status': 'error', 'message': 'Prompt is required.'}), 400

    # Aspect ratio for image output (whitelist-validated to prevent injection)
    _valid_ratios = {'1:1', '16:9', '9:16', '4:3', '3:4', '3:2', '2:3'}
    aspect_ratio  = body.get('aspect_ratio', '1:1')
    if aspect_ratio not in _valid_ratios:
        aspect_ratio = '1:1'

    # Clean the base64 prefix if present
    ref_mime = 'image/jpeg'
    ref_b64  = ''
    if image_b64:
        ref_b64 = image_b64
        if ',' in image_b64:
            header, ref_b64 = image_b64.split(',', 1)
            if 'image/' in header:
                ref_mime = header.split(':')[1].split(';')[0]

    error_logs = []

    # ── STEP 1: Quick vision analysis to extract subject description ─────────────
    # Only used as a fallback hint for OpenAI (which can’t see the image directly)
    subject_desc = ""
    if user_gemini_key and ref_b64:
        try:
            vurl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={user_gemini_key}"
            vp = {
                "contents": [{"parts": [
                    {"text": "Describe the person in this photo in 2 sentences covering their face, skin tone, hair, and approximate age. Be concise and specific."},
                    {"inlineData": {"mimeType": ref_mime, "data": ref_b64}}
                ]}]
            }
            vreq = urllib.request.Request(vurl, data=json.dumps(vp).encode(), headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(vreq, timeout=20) as vr:
                subject_desc = json.loads(vr.read().decode())['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            error_logs.append(f"Vision: {e}")

    # ── Build the generation prompt ───────────────────────────────────────────
    if ref_b64:
        # IMAGE-EDITING MODE: send both image + prompt to Gemini
        # The model sees the uploaded photo and applies the user’s prompt as a scene edit.
        gen_prompt = (
            f"Using the person in the reference image as the subject, create this scene: {prompt}\n\n"
            f"Requirements:\n"
            f"- Preserve the person’s exact face, skin tone, hair, and physical appearance from the reference photo.\n"
            f"- Only change the scene, background, clothing, or context as described above.\n"
            f"- Output a high-quality, photorealistic image."
        )
        # Fallback hint for OpenAI (which cannot see the image)
        openai_prompt = (
            f"A photorealistic portrait of a person ({subject_desc or 'as described below'}) "
            f"in the following scene: {prompt}. High quality, cinematic."
        )
    else:
        # TEXT-TO-IMAGE MODE
        gen_prompt     = f"{prompt}\n\nStyle: high quality, cinematic, photorealistic."
        openai_prompt  = gen_prompt

    # ── STEP 2: Gemini Image Generation (user's personal API key) ─────────────
    if user_gemini_key:
        # Image-editing models — send the reference image when available so the
        # model treats the request as image-to-image, not text-to-image.
        # See https://ai.google.dev/gemini-api/docs/image-generation
        GEMINI_IMAGE_MODELS = [
            'gemini-2.0-flash-preview-image-generation',  # primary image gen model
            'gemini-2.0-flash-exp',                        # experimental fallback
        ]

        # Order matters: image first so Gemini treats it as an editing request
        content_parts = []
        if ref_b64:
            content_parts.append({"inlineData": {"mimeType": ref_mime, "data": ref_b64}})
        content_parts.append({"text": gen_prompt})

        for model_name in GEMINI_IMAGE_MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={user_gemini_key}"
                payload = {
                    "contents": [{"parts": content_parts}],
                    "generationConfig": {
                        "responseModalities": ["TEXT", "IMAGE"],
                        "imageConfig": {"aspectRatio": aspect_ratio}
                    }
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=90) as resp:
                    res_data = json.loads(resp.read().decode())

                if 'candidates' in res_data:
                    # Iterate in reverse — skip thought parts, grab the final image
                    parts = res_data['candidates'][0].get('content', {}).get('parts', [])
                    for part in reversed(parts):
                        if part.get('thought'):
                            continue
                        if 'inlineData' in part:
                            img_b64_enc = part['inlineData']['data']
                            mime = part['inlineData'].get('mimeType', 'image/png')
                            return jsonify({'status': 'success', 'image_b64': f"data:{mime};base64,{img_b64_enc}", 'mime_type': mime})

                error_logs.append(f"Gemini/{model_name}: returned no image part.")
            except urllib.error.HTTPError as he:
                err_body = he.read().decode()[:400]
                error_logs.append(f"Gemini/{model_name}: HTTP {he.code} — {err_body}")
            except Exception as ex:
                error_logs.append(f"Gemini/{model_name}: {str(ex)}")

    # ── STEP 3: OpenAI DALL-E 3 Fallback ────────────────────────────────────
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/images/generations"
            payload = {
                "model": "dall-e-3",
                "prompt": openai_prompt[:1000],
                "n": 1,
                "size": "1024x1024",
                "response_format": "b64_json"
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode())
                if 'data' in res_data and len(res_data['data']) > 0:
                    img_b64_enc = res_data['data'][0]['b64_json']
                    return jsonify({'status': 'success', 'image_b64': f"data:image/png;base64,{img_b64_enc}", 'mime_type': 'image/png'})
                error_logs.append("OpenAI returned no image data.")
        except urllib.error.HTTPError as he:
            error_logs.append(f"OpenAI/DALL-E 3: HTTP {he.code} — {he.read().decode()[:200]}")
        except Exception as ex:
            error_logs.append(f"OpenAI/DALL-E 3: {str(ex)}")

    if not user_gemini_key and not OPENAI_API_KEY:
        return jsonify({'status': 'error', 'message': 'No API keys configured for your account.'}), 500

    error_summary = " | ".join(error_logs)
    return jsonify({'status': 'error', 'message': f'Image generation failed. Details: {error_summary}'}), 500


# ─────────────────────────────────────────────────────────────
# STATIC / SEO helpers
# ─────────────────────────────────────────────────────────────
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/ads.txt')
def ads_txt():
    # ads.txt must be served from the ROOT of the domain, not /static/
    # Use absolute path to guarantee it works regardless of working directory
    from flask import Response
    ads_content = "google.com, pub-5050768956635718, DIRECT, f08c47fec0942fa0\n"
    return Response(ads_content, mimetype='text/plain', headers={
        'Cache-Control': 'public, max-age=86400',
        'X-Robots-Tag': 'noindex',
    })

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(app.root_path, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    from flask import Response
    # Get current prompts for dynamic sitemap entries
    try:
        data = fetch_data()
        prompts = data.get('prompts', []) or []
    except Exception:
        prompts = []
    
    BASE = 'https://video-prompts-gallery.onrender.com'
    TODAY = '2026-04-18'
    
    urls = [
        f'<url><loc>{BASE}/</loc><changefreq>daily</changefreq><priority>1.0</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/about</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/contact</loc><changefreq>monthly</changefreq><priority>0.7</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog</loc><changefreq>weekly</changefreq><priority>0.9</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/how-to-write-ai-video-prompts</loc><changefreq>monthly</changefreq><priority>0.85</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/runway-ml-vs-pika-labs</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/cinematic-lighting-prompts</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/ai-video-prompts-for-social-media</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/nature-landscape-prompts</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
        f'<url><loc>{BASE}/blog/scifi-cinematic-prompts</loc><changefreq>monthly</changefreq><priority>0.8</priority><lastmod>{TODAY}</lastmod></url>',
    ]
    
    # Add individual prompt deep-link URLs for SEO
    for p in prompts:
        pid = p.get('Unique ID', '')
        if pid:
            urls.append(f'<url><loc>{BASE}/?prompt_id={pid}</loc><changefreq>monthly</changefreq><priority>0.7</priority><lastmod>{TODAY}</lastmod></url>')

    sitemap_body = '\n'.join(urls)
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_body}
</urlset>'''
    
    return Response(sitemap, mimetype='application/xml', headers={
        'Cache-Control': 'public, max-age=3600',
        'X-Robots-Tag': 'noindex'  # Don't index the sitemap itself
    })


@app.route('/robots.txt')
def robots_txt():
    from flask import Response
    content = """User-agent: *
Allow: /
Allow: /ads.txt
Allow: /sitemap.xml
Disallow: /api/
Disallow: /admin/

User-agent: Mediapartners-Google
Allow: /

User-agent: AdsBot-Google
Allow: /

Sitemap: https://video-prompts-gallery.onrender.com/sitemap.xml
"""
    return Response(content, mimetype='text/plain', headers={'Cache-Control': 'public, max-age=86400'})


@app.route('/ads.txt')
def ads_txt():
    """Serve ads.txt directly — Google AdSense crawler MUST be able to fetch this."""
    from flask import Response
    content = "google.com, pub-5050768956635718, DIRECT, f08c47fec0942fa0\n"
    return Response(content, mimetype='text/plain', headers={
        'Cache-Control': 'public, max-age=86400',
        'X-Content-Type-Options': 'nosniff'
    })


@app.route('/favicon.png')
@app.route('/favicon.ico')
def favicon():   return send_from_directory('static', 'favicon.png')

@app.route('/google7b16d249e9588da5.html')
def google_verification():
    return send_from_directory('static', 'google7b16d249e9588da5.html')

@app.route('/healthz')
def healthz():   return 'OK', 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port)
