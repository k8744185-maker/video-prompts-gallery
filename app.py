import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import time
import html
import re

# Load environment variables
# For local development, load from .env file
# For Streamlit Cloud, load from secrets
load_dotenv()

# Security Configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minutes in seconds
SESSION_TIMEOUT = 1800  # 30 minutes in seconds
MAX_PROMPT_LENGTH = 5000
MAX_NAME_LENGTH = 200

# Page configuration
st.set_page_config(
    page_title="Video Prompts Gallery",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Main background with animated gradient */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-size: 200% 200%;
        animation: gradientShift 15s ease infinite;
        padding: 1rem;
        min-height: 100vh;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-size: 200% 200%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Hero section with glassmorphism */
    .hero {
        text-align: center;
        padding: 3rem 2rem;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 30px;
        margin-bottom: 2.5rem;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.8s ease;
    }
    
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .hero h1 {
        font-size: 3.5rem;
        color: white;
        margin-bottom: 0.8rem;
        text-shadow: 2px 4px 8px rgba(0,0,0,0.15);
        font-weight: 800;
        letter-spacing: -1px;
    }
    
    .hero p {
        font-size: 1.3rem;
        color: rgba(255, 255, 255, 0.95);
        font-weight: 500;
        letter-spacing: 0.3px;
    }
    
    /* Tabs styling with modern effects */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.8rem;
        background: rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 0.6rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .stTabs [data-baseweb="tab"] {
        color: white !important;
        font-weight: 600;
        font-size: 1.05rem;
        padding: 1rem 2.5rem;
        border-radius: 15px;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        position: relative;
        overflow: hidden;
    }
    
    .stTabs [data-baseweb="tab"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stTabs [data-baseweb="tab"]:hover::before {
        left: 100%;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #667eea !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
    }
    
    /* Info box styling with animations */
    .stAlert {
        border-radius: 18px;
        border: none;
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        animation: slideInLeft 0.5s ease;
        backdrop-filter: blur(10px);
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Enhanced Button styling with ripple effect */
    .stButton > button {
        border-radius: 14px;
        padding: 0.85rem 2.5rem;
        font-weight: 600;
        border: none;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        position: relative;
        overflow: hidden;
        font-size: 1rem;
        letter-spacing: 0.3px;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Input styling with focus effects */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 14px;
        border: 2px solid rgba(255, 255, 255, 0.4);
        background: rgba(255, 255, 255, 0.95) !important;
        color: #1a1a1a !important;
        font-size: 1.05rem;
        padding: 1rem 1.25rem;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        background: white !important;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15), 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    
    /* Input placeholder with better styling */
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #888 !important;
        font-weight: 400;
    }
    
    /* Input labels */
    .stTextInput label,
    .stTextArea label {
        font-weight: 600 !important;
        color: white !important;
        font-size: 1.05rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Premium Prompt card with 3D effects */
    .prompt-container {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 24px;
        padding: 0;
        margin: 3rem 0;
        box-shadow: 0 12px 40px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(102, 126, 234, 0.1);
        overflow: hidden;
        position: relative;
        animation: fadeInUp 0.6s ease;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .prompt-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.7s;
    }
    
    .prompt-container:hover::before {
        left: 100%;
    }
    
    .prompt-container:hover {
        transform: translateY(-12px) scale(1.02);
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.25), 0 8px 16px rgba(0,0,0,0.08);
        border-color: rgba(102, 126, 234, 0.4);
    }
    
    .prompt-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    
    .prompt-header::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
        border-radius: 50%;
        transform: translate(50%, -50%);
    }
    
    .prompt-body {
        padding: 2.5rem;
        background: white;
    }
    
    .prompt-footer {
        background: linear-gradient(to right, #f8f9fa, #ffffff);
        padding: 1.5rem 2.5rem;
        border-top: 1px solid rgba(0,0,0,0.06);
    }
    
    .prompt-number {
        font-size: 1.6rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 1rem;
    }
    
    /* Enhanced animations */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .stSuccess {
        animation: slideIn 0.5s ease;
        border-radius: 16px !important;
        border-left: 4px solid #10b981 !important;
        background: linear-gradient(to right, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05)) !important;
    }
    
    .stError {
        border-radius: 16px !important;
        border-left: 4px solid #ef4444 !important;
        background: linear-gradient(to right, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05)) !important;
    }
    
    .stWarning {
        border-radius: 16px !important;
        border-left: 4px solid #f59e0b !important;
        background: linear-gradient(to right, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05)) !important;
    }
    
    .stInfo {
        border-radius: 16px !important;
        border-left: 4px solid #3b82f6 !important;
        background: linear-gradient(to right, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05)) !important;
    }
    
    /* Code block with premium styling */
    .stCodeBlock {
        border-radius: 14px;
        background: #f8f9fa !important;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.06);
    }
    
    /* Headers with better hierarchy */
    h1, h2, h3 {
        color: white !important;
        font-weight: 700 !important;
    }
    
    h1 {
        font-size: 2.5rem !important;
        letter-spacing: -0.5px !important;
    }
    
    h2 {
        font-size: 2rem !important;
        letter-spacing: -0.3px !important;
    }
    
    h3 {
        font-size: 1.6rem !important;
        margin-top: 1.5rem !important;
        letter-spacing: -0.2px !important;
    }
    
    /* Divider with gradient */
    hr {
        margin: 2.5rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.3), transparent);
    }
    
    /* Selectbox with modern styling */
    .stSelectbox > div > div {
        border-radius: 14px;
        background: white;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    /* Columns spacing */
    [data-testid="column"] {
        padding: 0 0.75rem;
    }
    
    /* Form styling with glassmorphism */
    .stForm {
        background: rgba(255, 255, 255, 0.08);
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
    }
    
    /* Spinner/Loading state */
    .stSpinner > div {
        border-color: rgba(255, 255, 255, 0.3) !important;
        border-top-color: white !important;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.5);
    }
    
    /* Tooltip enhancement */
    [data-testid="stTooltipIcon"] {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Search box enhancement */
    .stTextInput[data-testid="stTextInput"] {
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Security Functions
def sanitize_input(text):
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return ""
    # Remove any HTML tags and escape special characters
    text = html.escape(str(text))
    # Remove any potential script injections
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    return text.strip()

def validate_input(text, max_length):
    """Validate input length and content"""
    if not text or not text.strip():
        return False, "Input cannot be empty"
    if len(text) > max_length:
        return False, f"Input too long (max {max_length} characters)"
    # Check for suspicious patterns
    suspicious_patterns = [
        r'\.\.[\\/]',  # Path traversal
        r'<\s*iframe',  # iframe injection
        r'<\s*embed',   # embed injection
        r'<\s*object',  # object injection
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Input contains suspicious content"
    return True, ""

def hash_password(password):
    """Hash password with SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_rate_limit(session_key):
    """Check if user has exceeded login attempts"""
    current_time = time.time()
    
    if f'{session_key}_attempts' not in st.session_state:
        st.session_state[f'{session_key}_attempts'] = 0
        st.session_state[f'{session_key}_lockout_until'] = 0
    
    # Check if still in lockout period
    if current_time < st.session_state[f'{session_key}_lockout_until']:
        remaining = int(st.session_state[f'{session_key}_lockout_until'] - current_time)
        return False, f"Too many failed attempts. Try again in {remaining} seconds."
    
    # Reset attempts if lockout period has passed
    if current_time >= st.session_state[f'{session_key}_lockout_until']:
        st.session_state[f'{session_key}_attempts'] = 0
    
    return True, ""

def record_failed_attempt(session_key):
    """Record a failed login attempt"""
    st.session_state[f'{session_key}_attempts'] += 1
    
    if st.session_state[f'{session_key}_attempts'] >= MAX_LOGIN_ATTEMPTS:
        st.session_state[f'{session_key}_lockout_until'] = time.time() + LOCKOUT_TIME
        st.session_state[f'{session_key}_attempts'] = 0

def check_session_timeout():
    """Check if session has timed out"""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
        return True
    
    current_time = time.time()
    if current_time - st.session_state.last_activity > SESSION_TIMEOUT:
        # Session expired
        st.session_state.authenticated = False
        st.session_state.last_activity = current_time
        return False
    
    # Update last activity time
    st.session_state.last_activity = current_time
    return True

# Google Sheets setup
def get_google_sheet():
    """Connect to Google Sheets - Works with both local and Streamlit Cloud"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Check if running locally (credentials.json exists) or on Streamlit Cloud
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
        if os.path.exists(creds_path) and os.path.exists('.env'):
            # Local development - use credentials.json file
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            sheet_id = os.getenv('GOOGLE_SHEET_ID')
        else:
            # Streamlit Cloud - use secrets
            creds_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            sheet_id = st.secrets['GOOGLE_SHEET_ID']
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Create headers if sheet is empty
        try:
            headers = sheet.row_values(1)
            if not headers or headers != ['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID']:
                sheet.update('A1:E1', [['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID']])
        except:
            sheet.update('A1:E1', [['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID']])
        
        return sheet
    except Exception as e:
        st.error(f"Google Sheets connection failed: {str(e)}")
        return None

def generate_unique_id():
    """Generate a unique ID based on timestamp"""
    timestamp = str(time.time()).replace('.', '')
    return f"PR{timestamp[-10:]}"

def save_prompt(sheet, prompt_name, prompt, video_id="", row_num=None):
    """Save or update prompt to Google Sheets with security validation"""
    try:
        # Validate inputs
        valid_name, msg_name = validate_input(prompt_name, MAX_NAME_LENGTH)
        if not valid_name:
            st.error(f"❌ Prompt Name: {msg_name}")
            return False
        
        valid_prompt, msg_prompt = validate_input(prompt, MAX_PROMPT_LENGTH)
        if not valid_prompt:
            st.error(f"❌ Prompt Text: {msg_prompt}")
            return False
        
        # Sanitize all inputs
        prompt_name = sanitize_input(prompt_name)
        prompt = sanitize_input(prompt)
        video_id = sanitize_input(video_id) if video_id else ""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if row_num:  # Update existing row
            # Get existing unique ID
            existing_data = sheet.row_values(row_num)
            unique_id = existing_data[1] if len(existing_data) > 1 else generate_unique_id()
            sheet.update(f'A{row_num}:E{row_num}', [[timestamp, unique_id, prompt_name, prompt, video_id]])
        else:  # Add new row
            unique_id = generate_unique_id()
            sheet.append_row([timestamp, unique_id, prompt_name, prompt, video_id])
        return True
    except Exception as e:
        st.error(f"Error saving prompt: {str(e)}")
        return False

def delete_prompt(sheet, row_num):
    """Delete prompt from Google Sheets"""
    try:
        sheet.delete_rows(row_num)
        return True
    except Exception as e:
        st.error(f"Error deleting prompt: {str(e)}")
        return False

def get_all_prompts(sheet):
    """Get all prompts from Google Sheets"""
    try:
        data = sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Error fetching prompts: {str(e)}")
        return []

def show_google_ad(ad_slot="", ad_format="auto", full_width=True):
    """Display Google AdSense ad"""
    # Get ads client ID - check local first, then secrets
    if os.path.exists('.env'):
        ads_client_id = os.getenv('GOOGLE_ADS_CLIENT_ID', '')
    else:
        ads_client_id = st.secrets.get('GOOGLE_ADS_CLIENT_ID', '')
    
    if not ads_client_id or ads_client_id == 'ca-pub-xxxxxxxxxxxxxxxxx':
        # Show placeholder when ads not configured
        st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 15px; text-align: center; 
                        margin: 1rem 0; border: 2px dashed rgba(255,255,255,0.3);">
                <p style="color: white; margin: 0; font-size: 0.9rem; opacity: 0.8;">📢 Advertisement Space</p>
                <p style="color: white; margin: 0.5rem 0 0 0; font-size: 0.75rem; opacity: 0.6;">Configure GOOGLE_ADS_CLIENT_ID in .env to show ads</p>
            </div>
        """, unsafe_allow_html=True)
        return
    
    # Google AdSense code
    ad_html = f"""
        <div style="margin: 1.5rem 0; text-align: center;">
            <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ads_client_id}"
                    crossorigin="anonymous"></script>
            <ins class="adsbygoogle"
                 style="display:block"
                 data-ad-client="{ads_client_id}"
                 data-ad-slot="{ad_slot}"
                 data-ad-format="{ad_format}"
                 data-full-width-responsive="{str(full_width).lower()}"></ins>
            <script>
                 (adsbygoogle = window.adsbygoogle || []).push({{}});
            </script>
        </div>
    """
    st.components.html(ad_html, height=200)

# Check admin authentication
def check_admin_password(key_suffix=""):
    """Check if admin password is correct with rate limiting and session timeout"""
    # Get admin password - check local first, then secrets
    if os.path.exists('.env'):
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    else:
        admin_password = st.secrets['ADMIN_PASSWORD']
    
    # Hash the stored password for comparison
    admin_password_hash = hash_password(admin_password)
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Check session timeout for authenticated users
    if st.session_state.authenticated:
        if not check_session_timeout():
            st.warning("⏱️ Session expired. Please login again.")
            st.session_state.authenticated = False
            st.rerun()
        return True
    
    if not st.session_state.authenticated:
        # Check rate limiting
        can_attempt, rate_msg = check_rate_limit(f"login_{key_suffix}")
        
        with st.form(f"login_form_{key_suffix}"):
            st.markdown("### 🔐 Admin Login")
            st.info("🔒 Secure login with rate limiting and session timeout")
            
            if not can_attempt:
                st.error(f"🚫 {rate_msg}")
                password = st.text_input("Password:", type="password", disabled=True)
                login = st.form_submit_button("Login", disabled=True)
            else:
                password = st.text_input("Password:", type="password", max_chars=100)
                login = st.form_submit_button("Login")
            
            if login and can_attempt:
                if password and len(password) > 0:
                    # Hash entered password and compare
                    entered_password_hash = hash_password(password)
                    if entered_password_hash == admin_password_hash:
                        st.session_state.authenticated = True
                        st.session_state.last_activity = time.time()
                        st.session_state[f'login_{key_suffix}_attempts'] = 0
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        record_failed_attempt(f"login_{key_suffix}")
                        remaining_attempts = MAX_LOGIN_ATTEMPTS - st.session_state.get(f'login_{key_suffix}_attempts', 0)
                        if remaining_attempts > 0:
                            st.error(f"❌ Incorrect password! {remaining_attempts} attempts remaining.")
                        else:
                            st.error(f"🚫 Too many failed attempts. Locked out for {LOCKOUT_TIME//60} minutes.")
                else:
                    st.warning("⚠️ Please enter a password")
        return False
    
    return True

# Main app
def main():
    # Show loading indicator
    with st.spinner('⏳ Please wait, loading...'):
        # Connect to Google Sheets
        sheet = get_google_sheet()
        
        if not sheet:
            st.error("⚠️ Unable to connect to database. Please check configuration.")
            return
    
    # Check if specific prompt is requested via URL
    query_params = st.query_params
    if "prompt_id" in query_params:
        # NO hero section for single prompt view
        show_single_prompt(sheet, query_params["prompt_id"])
        return
    
    # Hero section (only for main page)
    st.markdown("""
        <div class="hero">
            <h1>🎬 Video Prompts Gallery</h1>
            <p>Discover and share amazing AI video generation prompts</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show ad after hero
    show_google_ad(ad_slot="1234567890", ad_format="horizontal")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📝 Add New", "📚 View All Prompts", "✏️ Manage"])
    
    with tab1:
        st.markdown("### ✨ Create New Prompt")
        
        # Check admin authentication
        if check_admin_password("add"):
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🚪 Logout", key="logout", use_container_width=True):
                    with st.spinner('Logging out...'):
                        st.session_state.authenticated = False
                        time.sleep(0.3)
                        st.rerun()
            
            st.markdown("")  # Spacing
            
            with st.form("prompt_form", clear_on_submit=True):
                prompt_name = st.text_input(
                    "🎯 Prompt Name",
                    placeholder="e.g., Futuristic City, Sunset Beach, Space Adventure...",
                    help="Give a short catchy name for your prompt"
                )
                
                prompt = st.text_area(
                    "🎥 Your Video Prompt",
                    placeholder="Describe the amazing video you created with AI...\n\nExample: A cinematic shot of a futuristic city at sunset, with flying cars and neon lights...",
                    height=180,
                    help="Enter the prompt you used to generate your video"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    video_id = st.text_input(
                        "📹 Video ID (Optional)",
                        placeholder="e.g., video_001"
                    )
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("")  # Spacing
                submitted = st.form_submit_button("💾 Save Prompt", use_container_width=True, type="primary")
                
                if submitted:
                    if prompt.strip() and prompt_name.strip():
                        with st.spinner('Saving prompt...'):
                            if save_prompt(sheet, prompt_name.strip(), prompt.strip(), video_id.strip()):
                                st.success("✅ Prompt saved successfully!")
                                st.balloons()
                                time.sleep(0.5)
                                st.rerun()
                    else:
                        st.warning("⚠️ Please enter both prompt name and prompt text!")
    
    with tab2:
        st.markdown("### 🌟 All Prompts")
        
        # Get all prompts
        with st.spinner('⏳ Please wait, loading prompts...'):
            prompts = get_all_prompts(sheet)
        
        if prompts:
            # Stats at top
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Prompts", len(prompts))
            with col2:
                st.metric("🆕 Latest", f"#{len(prompts)}")
            with col3:
                st.metric("🎬 Videos", len([p for p in prompts if p.get('Video ID')]))
            
            st.markdown("---")
            
            # Show ad before prompts
            show_google_ad(ad_slot="1234567891", ad_format="auto")
            
            # Get base URL - check local first, then secrets
            if os.path.exists('.env'):
                base_url = os.getenv('BASE_URL', 'http://localhost:8501')
            else:
                base_url = st.secrets.get('BASE_URL', 'http://localhost:8501')
            
            # Search box
            search_query = st.text_input("🔍 Search prompts...", placeholder="Type to filter prompts")
            
            # Display prompts in reverse order (newest first)
            for idx, prompt_data in enumerate(reversed(prompts)):
                prompt_num = len(prompts) - idx
                unique_id = prompt_data.get('Unique ID', f'PR{str(prompt_num).zfill(4)}')
                prompt_name = prompt_data.get('Prompt Name', f'Prompt {prompt_num}')
                prompt_text = prompt_data.get('Prompt', 'N/A')
                
                # Skip empty prompts
                if not prompt_text or prompt_text.strip() == '' or prompt_text == 'N/A':
                    continue
                
                # Filter by search
                if search_query and search_query.lower() not in prompt_text.lower():
                    continue
                
                share_link = f"{base_url}?prompt_id={unique_id}"
                
                # Main card container
                st.markdown('<div class="prompt-container">', unsafe_allow_html=True)
                
                # HEADER SECTION (Purple gradient) - Show Prompt Name
                st.markdown(f'''
                    <div class="prompt-header">
                        <h2 style="margin: 0; font-size: 1.8rem; color: white;">🎬 {prompt_name}</h2>
                        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.95rem;">Prompt #{prompt_num}</p>
                    </div>
                ''', unsafe_allow_html=True)
                
                # BODY SECTION (Main content)
                st.markdown('<div class="prompt-body">', unsafe_allow_html=True)
                
                # Prompt Text Display
                st.markdown("### 📝 Prompt Text")
                st.markdown(f"""
                    <div style="background: white; padding: 2rem; border-radius: 15px; 
                                border-left: 6px solid #667eea; margin: 1rem 0; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <p style="color: #1a1a1a; font-size: 1.2rem; line-height: 1.9; margin: 0; font-weight: 500;">
                            {prompt_text}
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Action Buttons - Copy for all, Share for admin only
                if st.session_state.get('authenticated', False):
                    # Admin: Both buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Copy Prompt Text", key=f"copy_{idx}_{prompt_num}", use_container_width=True, type="secondary"):
                            st.session_state[f"show_copy_{idx}"] = True
                    with col2:
                        if st.button("🔗 Share Link", key=f"share_{idx}_{prompt_num}", use_container_width=True, type="secondary"):
                            st.session_state[f"show_link_{idx}"] = True
                else:
                    # Public users: Only copy button
                    if st.button("📋 Copy Prompt Text", key=f"copy_{idx}_{prompt_num}", use_container_width=True, type="primary"):
                        st.session_state[f"show_copy_{idx}"] = True
                
                # Show copy prompt if button clicked
                if st.session_state.get(f"show_copy_{idx}", False):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.success("✅ Select the text below and press Ctrl+C (or Cmd+C on Mac) to copy:")
                    st.text_area(
                        "Prompt Text",
                        value=prompt_text,
                        height=150,
                        key=f"textarea_{idx}_{prompt_num}",
                        label_visibility="collapsed"
                    )
                    if st.button("✕ Close", key=f"close_copy_{idx}_{prompt_num}", type="primary"):
                        st.session_state[f"show_copy_{idx}"] = False
                        st.rerun()
                
                # Show share link if button clicked (admin only)
                if st.session_state.get(f"show_link_{idx}", False) and st.session_state.get('authenticated', False):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("🔗 Share this unique link:")
                    st.code(share_link, language="text")
                    if st.button("✕ Close", key=f"close_{idx}_{prompt_num}", type="primary"):
                        st.session_state[f"show_link_{idx}"] = False
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # FOOTER SECTION - Only show for admin
                if st.session_state.get('authenticated', False):
                    st.markdown('<div class="prompt-footer">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        if prompt_data.get('Video ID'):
                            st.markdown(f"**📹 Video ID:** `{prompt_data.get('Video ID')}`")
                        else:
                            st.markdown("**📹 Video ID:** _Not specified_")
                    with col2:
                        st.markdown(f"**🕒 Created:** {prompt_data.get('Timestamp', 'N/A')}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show ad after every 3 prompts
                if (idx + 1) % 3 == 0 and (idx + 1) < len(prompts):
                    show_google_ad(ad_slot=f"123456789{(idx+1)//3}", ad_format="auto")
        else:
            st.info("📭 No prompts yet. Add your first prompt in the 'Add New' tab!")
    
    with tab3:
        st.markdown("### ⚙️ Manage Prompts")
        
        # Check admin authentication
        if check_admin_password("edit"):
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🚪 Logout", key="logout_edit", use_container_width=True):
                    with st.spinner('Logging out...'):
                        st.session_state.authenticated = False
                        time.sleep(0.3)
                        st.rerun()
            
            st.markdown("")  # Spacing
            
            # Get all prompts
            with st.spinner('⏳ Please wait, loading prompts...'):
                prompts = get_all_prompts(sheet)
            
            if prompts:
                # Select prompt to edit
                st.markdown("**Select a prompt to edit or delete:**")
                prompt_options = [f"#{i+1} - {p.get('Prompt Name', 'Untitled')} - {p.get('Prompt', '')[:40]}..." for i, p in enumerate(prompts)]
                selected_idx = st.selectbox(
                    "Choose prompt:",
                    range(len(prompts)),
                    format_func=lambda x: prompt_options[x],
                    label_visibility="collapsed"
                )
                
                selected_prompt = prompts[selected_idx]
                row_num = selected_idx + 2  # +2 because row 1 is header
                
                st.markdown("---")
                
                # Edit form
                with st.form("edit_form"):
                    st.markdown(f"### Editing Prompt #{selected_idx + 1}")
                    
                    edited_prompt_name = st.text_input(
                        "🎯 Prompt Name:",
                        value=selected_prompt.get('Prompt Name', ''),
                        placeholder="e.g., Futuristic City, Sunset Beach..."
                    )
                    
                    edited_prompt = st.text_area(
                        "🎥 Prompt Text:",
                        value=selected_prompt.get('Prompt', ''),
                        height=150
                    )
                    
                    edited_video_id = st.text_input(
                        "📹 Video ID:",
                        value=selected_prompt.get('Video ID', '')
                    )
                    
                    st.markdown("")  # Spacing
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_btn = st.form_submit_button(
                            "💾 Update Prompt",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    with col2:
                        delete_btn = st.form_submit_button(
                            "🗑️ Delete Prompt",
                            use_container_width=True
                        )
                    
                    if update_btn:
                        if edited_prompt.strip() and edited_prompt_name.strip():
                            with st.spinner('Updating prompt...'):
                                if save_prompt(sheet, edited_prompt_name.strip(), edited_prompt.strip(), edited_video_id.strip(), row_num):
                                    st.success("✅ Prompt updated successfully!")
                                    time.sleep(0.5)
                                    st.rerun()
                        else:
                            st.warning("⚠️ Prompt name and text cannot be empty!")
                    
                    if delete_btn:
                        with st.spinner('Deleting prompt...'):
                            if delete_prompt(sheet, row_num):
                                st.success("✅ Prompt deleted successfully!")
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.info("📭 No prompts to manage yet.")

def show_single_prompt(sheet, prompt_id):
    """Show a single prompt page - Ultra compact with no hero section"""
    try:
        # Get all prompts
        with st.spinner('⏳ Please wait, loading prompt...'):
            prompts = get_all_prompts(sheet)
        
        # Find the prompt with matching unique ID
        prompt_data = None
        for prompt in prompts:
            if prompt.get('Unique ID') == prompt_id:
                prompt_data = prompt
                break
        
        if prompt_data:
            prompt_name = prompt_data.get('Prompt Name', 'Untitled Prompt')
            prompt_text = prompt_data.get('Prompt', 'N/A')
            
            # Skip empty prompts
            if not prompt_text or prompt_text.strip() == '' or prompt_text == 'N/A':
                st.error("❌ Prompt not found!")
                if st.button("📚 View All Prompts", type="primary"):
                    st.query_params.clear()
                    st.rerun()
                return
            
            # Single compact card - NO separate hero
            st.markdown(f"""
                <div style="background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%); border-radius: 24px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.15); border: 1px solid rgba(102, 126, 234, 0.2); margin: 0.5rem auto; max-width: 900px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem; text-align: center;">
                        <h1 style="margin: 0; font-size: 1.6rem; color: white; font-weight: 700;">🎬 {prompt_name}</h1>
                    </div>
                    <div style="padding: 1.5rem;">
                        <div style="background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                            <p style="color: #1a1a1a; font-size: 1.1rem; line-height: 1.8; margin: 0; font-weight: 500; white-space: pre-wrap;">{prompt_text}</p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Show ad after prompt card
            show_google_ad(ad_slot="9876543210", ad_format="auto")
            
            # Buttons row
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Copy Text", key="copy_single_prompt", use_container_width=True, type="primary"):
                    st.session_state["show_copy_single"] = True
            with col2:
                if st.button("📚 View All Prompts", use_container_width=True, type="secondary"):
                    with st.spinner('Loading...'):
                        st.query_params.clear()
                        st.rerun()
            
            # Show copy prompt if button clicked
            if st.session_state.get("show_copy_single", False):
                st.markdown("<br>", unsafe_allow_html=True)
                st.success("✅ Select the text below and press Ctrl+C (or Cmd+C on Mac) to copy:")
                st.text_area(
                    "Prompt Text",
                    value=prompt_text,
                    height=200,
                    key="textarea_single_prompt",
                    label_visibility="collapsed"
                )
                if st.button("✕ Close", key="close_copy_single", type="primary"):
                    st.session_state["show_copy_single"] = False
                    st.rerun()
            
            # Metadata footer
            if prompt_data.get('Video ID') or prompt_data.get('Timestamp'):
                st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 0.6rem 1rem; border-radius: 12px; margin-top: 0.8rem; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.15); font-size: 0.85rem; color: white; display: flex; justify-content: space-between; flex-wrap: wrap;">
                        <span>📹 <strong>{prompt_data.get('Video ID', 'N/A')}</strong></span>
                        <span style="opacity: 0.9;">🕒 {prompt_data.get('Timestamp', 'N/A')}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.error("❌ Prompt not found!")
            if st.button("📚 View All Prompts", type="primary"):
                st.query_params.clear()
                st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading prompt: {str(e)}")
        if st.button("📚 View All Prompts", type="primary"):
            st.query_params.clear()
            st.rerun()
        st.error(f"❌ Error loading prompt: {str(e)}")
        if st.button("📚 View All Prompts", type="primary"):
            st.query_params.clear()
            st.rerun()

if __name__ == "__main__":
    main()
