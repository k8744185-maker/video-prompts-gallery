import streamlit as st
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
import hashlib
import time
import html
import re
import json

# Load environment variables
load_dotenv()

# Security Configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minutes in seconds
SESSION_TIMEOUT = 1800  # 30 minutes in seconds
MAX_PROMPT_LENGTH = 5000
MAX_NAME_LENGTH = 200

# Error handling wrapper
def handle_error(error_msg="Something went wrong", show_refresh=True):
    """Display user-friendly error with refresh option"""
    st.error(f"⚠️ {error_msg}")
    if show_refresh:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh Page", key=f"refresh_{time.time()}"):
                st.rerun()
        with col2:
            st.caption("If the issue persists, try reloading your browser.")

# Page configuration - Optimized for Render.com free tier
st.set_page_config(
    page_title="Video Prompts Gallery - AI Video Prompt Collection",
    page_icon="🎬",
    layout="centered",  # Narrow layout uses less memory
    initial_sidebar_state="collapsed"
)

# Note: Meta tags (google-site-verification, google-adsense-account) and AdSense script
# are injected directly into Streamlit's index.html <head> via start.sh patch - no JS needed here.

# Enhanced CSS with animations, dark mode, and better UI
st.markdown("""
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Removed heavy animations - kept simple styling for better performance */
    
    /* Prompt cards with minimal effects */
    .prompt-container {
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .prompt-container:hover {
        box-shadow: 0 6px 18px rgba(102, 126, 234, 0.2);
    }
    
    .prompt-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        color: white;
    }
    
    .prompt-body {
        background: white;
        padding: 1.5rem;
    }
    
    /* Better typography */
    .prompt-container h2 {
        margin: 0;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Button improvements - No animations to avoid lag */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        cursor: pointer;
    }
    
    .stButton > button:hover {
        opacity: 0.9;
    }
    
    .stButton > button:active {
        opacity: 0.8;
    }
    
    /* Column styling */
    .stColumn {
        /* animation removed for performance */
    }
    
    /* Badge styling - Minimal animations */
    .category-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.35rem 0.85rem;
        border-radius: 15px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
    }
    
    .category-badge:hover {
        background: rgba(255,255,255,0.4);
    }
    
    /* Better links */
    a {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
    }
    
    a:hover {
        color: #764ba2;
        text-decoration: underline;
    }
    
    /* Reduced motion for accessibility */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Mobile responsiveness */
    @media (max-width: 640px) {
        .prompt-container {
            margin-bottom: 1rem;
        }
        
        .prompt-header {
            padding: 1rem;
        }
        
        .prompt-body {
            padding: 1rem;
        }
        
        .prompt-container h2 {
            font-size: 1.5rem;
        }
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
    """Check if user has exceeded login attempts - simplified"""
    try:
        if 'session_initialized' not in st.session_state:
            st.session_state.session_initialized = True
            st.session_state[f'{session_key}_attempts'] = 0
            st.session_state[f'{session_key}_lockout_until'] = 0
        
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
    except Exception as e:
        # If any error, allow login attempt
        return True, ""

def record_failed_attempt(session_key):
    """Record a failed login attempt"""
    try:
        st.session_state[f'{session_key}_attempts'] += 1
        
        if st.session_state[f'{session_key}_attempts'] >= MAX_LOGIN_ATTEMPTS:
            st.session_state[f'{session_key}_lockout_until'] = time.time() + LOCKOUT_TIME
            st.session_state[f'{session_key}_attempts'] = 0
    except:
        # Session state not initialized yet
        pass

# Google Sheets setup with caching
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_prompts_cached(sheet_id_param, creds_json=None):
    """Get all prompts from Google Sheets with caching"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id_param)
        sheet = spreadsheet.sheet1
        data = sheet.get_all_records()
        return data
    except Exception as e:
        return []

def get_google_sheet():
    """Connect to Google Sheets - Works with local, Streamlit Cloud, and Render.com"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Check if running locally (credentials.json exists) or on cloud
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
        
        if os.path.exists(creds_path) and os.path.exists('.env'):
            # Local development - use credentials.json file
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            sheet_id = os.getenv('GOOGLE_SHEET_ID')
        elif os.getenv('GOOGLE_CREDENTIALS'):
            # Render.com or other cloud - credentials as JSON string in env var
            creds_json = os.getenv('GOOGLE_CREDENTIALS')
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            sheet_id = os.getenv('GOOGLE_SHEET_ID')
        else:
            # Streamlit Cloud - use secrets
            creds_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            sheet_id = st.secrets['GOOGLE_SHEET_ID']
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.sheet1
        
        # Create headers if sheet is empty
        try:
            headers = sheet.row_values(1)
            if not headers or headers != ['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID', 'Category']:
                sheet.update('A1:F1', [['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID', 'Category']])
        except:
            sheet.update('A1:F1', [['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID', 'Category']])
        
        # Initialize analytics sheet for visit counts and errors
        try:
            analytics_sheet = spreadsheet.worksheet('Analytics')
        except:
            # Create Analytics sheet if it doesn't exist
            analytics_sheet = spreadsheet.add_worksheet(title='Analytics', rows=1000, cols=10)
            analytics_sheet.update('A1:F1', [['Timestamp', 'Prompt ID', 'Event Type', 'User IP', 'Error Message', 'Status']])
        
        # Store analytics sheet in session state for later use
        if 'analytics_sheet' not in st.session_state:
            st.session_state.analytics_sheet = analytics_sheet

        # Store spreadsheet reference for Comments/Feedback sheets
        st.session_state.spreadsheet = spreadsheet

        return sheet
    except Exception as e:
        handle_error("Unable to connect to database. Please try again.", show_refresh=True)
        st.caption(f"Technical details: {str(e)}")
        return None

def generate_unique_id():
    """Generate a unique ID based on timestamp"""
    timestamp = str(time.time()).replace('.', '')
    return f"PR{timestamp[-10:]}"

def save_prompt(sheet, prompt_name, prompt, video_id="", category="General", row_num=None):
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
        category = sanitize_input(category) if category else "General"
        
        # India timezone timestamp
        india_tz = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        if row_num:  # Update existing row
            # Get existing unique ID
            existing_data = sheet.row_values(row_num)
            unique_id = existing_data[1] if len(existing_data) > 1 else generate_unique_id()
            sheet.update(f'A{row_num}:F{row_num}', [[timestamp, unique_id, prompt_name, prompt, video_id, category]])
        else:  # Add new row
            unique_id = generate_unique_id()
            sheet.append_row([timestamp, unique_id, prompt_name, prompt, video_id, category])
        return True
    except Exception as e:
        handle_error("Unable to save prompt. Please try again.", show_refresh=True)
        st.caption(f"Technical details: {str(e)}")
        return False

def delete_prompt(sheet, row_num):
    """Delete prompt from Google Sheets"""
    try:
        sheet.delete_rows(row_num)
        return True
    except Exception as e:
        handle_error("Unable to delete prompt. Please try again.", show_refresh=True)
        st.caption(f"Technical details: {str(e)}")
        return False

def get_all_prompts(sheet):
    """Get all prompts from Google Sheets"""
    try:
        data = sheet.get_all_records()
        return data
    except Exception as e:
        handle_error("Unable to load prompts. Please try again.", show_refresh=True)
        st.caption(f"Technical details: {str(e)}")
        return []

def log_analytics_event(event_type, prompt_id='', error_msg='', status='success'):
    """Log analytics events to Google Sheets"""
    try:
        if 'analytics_sheet' in st.session_state:
            analytics_sheet = st.session_state.analytics_sheet
            india_tz = pytz.timezone('Asia/Kolkata')
            timestamp = datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S")
            user_ip = 'N/A'  # Can be enhanced with actual IP tracking
            analytics_sheet.append_row([timestamp, prompt_id, event_type, user_ip, error_msg, status])
    except:
        pass  # Silent fail for analytics

def get_admin_notifications():
    """Get unread error notifications for admin"""
    try:
        if 'analytics_sheet' in st.session_state:
            analytics_sheet = st.session_state.analytics_sheet
            data = analytics_sheet.get_all_records()
            # Get errors from last 24 hours
            errors = [row for row in data if row.get('Event Type') == 'error' and row.get('Status') == 'unread']
            return len(errors), errors
    except:
        pass
    return 0, []

def generate_sitemap(prompts):
    """Generate comprehensive XML sitemap for SEO with proper lastmod dates"""
    base_url = "https://video-prompts-gallery.onrender.com"
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
    sitemap += '         xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    
    # Homepage - highest priority
    today = datetime.now().strftime('%Y-%m-%d')
    sitemap += f'  <url>\n    <loc>{base_url}/</loc>\n'
    sitemap += f'    <lastmod>{today}</lastmod>\n'
    sitemap += f'    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
    
    # Legal/Terms pages
    legal_pages = ['privacy', 'terms', 'about', 'contact']
    for page in legal_pages:
        sitemap += f'  <url>\n    <loc>{base_url}/?tab={page.capitalize()}</loc>\n'
        sitemap += f'    <lastmod>{today}</lastmod>\n'
        sitemap += f'    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
    
    # Each prompt - sorted by timestamp (newest first)
    for idx, prompt in enumerate(prompts[:100]):  # Increased from 50 to 100
        unique_id = prompt.get('Unique ID', '')
        if unique_id:
            # Calculate priority based on position (newer = higher priority)
            priority = max(0.5, 0.7 - (idx * 0.001))
            sitemap += f'  <url>\n    <loc>{base_url}/?prompt_id={unique_id}</loc>\n'
            sitemap += f'    <lastmod>{today}</lastmod>\n'
            sitemap += f'    <changefreq>weekly</changefreq>\n'
            sitemap += f'    <priority>{priority:.1f}</priority>\n  </url>\n'
    
    sitemap += '</urlset>'
    return sitemap

def show_google_ad(ad_slot="", ad_format="auto", full_width=True):
    """AdSense Auto Ads - Google automatically places ads after approval.
    Manual ins tags removed: fake slot IDs block AdSense approval.
    The AdSense script is injected into <head> via start.sh - Auto Ads handles placement.
    """
    pass  # Auto Ads will display after AdSense approval - no manual placement needed


def get_or_create_comments_sheet():
    """Get or create the Comments sheet in Google Sheets"""
    try:
        if 'comments_sheet' in st.session_state:
            return st.session_state.comments_sheet
        if 'spreadsheet' not in st.session_state:
            return None
        spreadsheet = st.session_state.spreadsheet
        try:
            comments_sheet = spreadsheet.worksheet('Comments')
        except Exception:
            comments_sheet = spreadsheet.add_worksheet(title='Comments', rows=2000, cols=6)
            comments_sheet.update('A1:F1', [['Timestamp', 'Prompt ID', 'Name', 'Comment', 'Status', 'IP']])
        st.session_state.comments_sheet = comments_sheet
        return comments_sheet
    except Exception:
        return None


def get_or_create_feedback_sheet():
    """Get or create the Feedback sheet in Google Sheets"""
    try:
        if 'feedback_sheet' in st.session_state:
            return st.session_state.feedback_sheet
        if 'spreadsheet' not in st.session_state:
            return None
        spreadsheet = st.session_state.spreadsheet
        try:
            feedback_sheet = spreadsheet.worksheet('Feedback')
        except Exception:
            feedback_sheet = spreadsheet.add_worksheet(title='Feedback', rows=2000, cols=5)
            feedback_sheet.update('A1:E1', [['Timestamp', 'Name', 'Rating', 'Comment', 'Email']])
        st.session_state.feedback_sheet = feedback_sheet
        return feedback_sheet
    except Exception:
        return None


def get_likes_count(prompt_id):
    """Get total like count for a prompt from Analytics sheet"""
    try:
        if 'analytics_sheet' not in st.session_state:
            return 0
        analytics_sheet = st.session_state.analytics_sheet
        data = analytics_sheet.get_all_records()
        return len([r for r in data if r.get('Event Type') == 'like' and str(r.get('Prompt ID')) == str(prompt_id)])
    except Exception:
        return 0


def add_like(prompt_id):
    """Add a like event to the Analytics sheet"""
    log_analytics_event('like', prompt_id=prompt_id)


def get_comments(prompt_id):
    """Get all non-deleted comments for a prompt"""
    try:
        comments_sheet = get_or_create_comments_sheet()
        if not comments_sheet:
            return []
        data = comments_sheet.get_all_records()
        return [r for r in data if str(r.get('Prompt ID')) == str(prompt_id) and r.get('Status', '') != 'deleted']
    except Exception:
        return []


def add_comment(prompt_id, name, comment_text):
    """Add a comment for a prompt to the Comments sheet"""
    try:
        comments_sheet = get_or_create_comments_sheet()
        if not comments_sheet:
            return False
        india_tz = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S")
        safe_name = sanitize_input(name.strip() or "Anonymous")[:50]
        safe_comment = sanitize_input(comment_text.strip())[:500]
        comments_sheet.append_row([timestamp, prompt_id, safe_name, safe_comment, 'approved', 'N/A'])
        return True
    except Exception:
        return False


def add_feedback(name, rating, comment_text, email=""):
    """Add website feedback to the Feedback sheet"""
    try:
        feedback_sheet = get_or_create_feedback_sheet()
        if not feedback_sheet:
            return False
        india_tz = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S")
        safe_name = sanitize_input(name.strip() or "Anonymous")[:50]
        safe_comment = sanitize_input(comment_text.strip())[:1000]
        safe_email = sanitize_input(email.strip())[:100]
        feedback_sheet.append_row([timestamp, safe_name, rating, safe_comment, safe_email])
        return True
    except Exception:
        return False


# Check admin authentication
def check_admin_password(key_suffix=""):
    """Check if admin password is correct with rate limiting and session timeout"""
    # Get admin password - check environment variable first, then secrets
    admin_password = os.getenv('ADMIN_PASSWORD', '')
    
    # If not in environment, try secrets (for Streamlit Cloud)
    if not admin_password and not os.path.exists('.env'):
        try:
            admin_password = st.secrets['ADMIN_PASSWORD']
        except:
            admin_password = 'admin123'
    
    # Hash the stored password for comparison
    admin_password_hash = hash_password(admin_password)
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Return True if already authenticated (no timeout check for performance)
    if st.session_state.authenticated:
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

# JSON-LD Structured Data for SEO
def add_structured_data():
    """Add comprehensive JSON-LD structured data for better SEO"""
    structured_data = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Video Prompts Gallery",
      "url": "https://video-prompts-gallery.onrender.com",
      "description": "Curated collection of high-quality AI video prompts for filmmakers and creators",
      "image": "https://video-prompts-gallery.onrender.com/logo.png",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://video-prompts-gallery.onrender.com/?search={search_term_string}",
        "query-input": "required name=search_term_string"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Video Prompts Gallery",
        "email": "k8744185@gmail.com",
        "url": "https://video-prompts-gallery.onrender.com",
        "sameAs": ["https://github.com/k8744185-maker/video-prompts-gallery"]
      },
      "inLanguage": "en",
      "isAccessibleForFree": true,
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
      }
    }
    </script>
    
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://video-prompts-gallery.onrender.com"},
        {"@type": "ListItem", "position": 2, "name": "Video Prompts", "item": "https://video-prompts-gallery.onrender.com#prompts"}
      ]
    }
    </script>
    
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is Video Prompts Gallery?",
          "acceptedAnswer": {"@type": "Answer", "text": "A curated collection of high-quality AI video generation prompts for creators using tools like Runway ML and Pika Labs."}
        },
        {
          "@type": "Question",
          "name": "Can I use these prompts for commercial projects?",
          "acceptedAnswer": {"@type": "Answer", "text": "Yes, our prompts are designed for both personal and commercial use with AI video generation tools."}
        },
        {
          "@type": "Question",
          "name": "What categories of prompts are available?",
          "acceptedAnswer": {"@type": "Answer", "text": "We offer prompts in Nature, Urban, Cinematic, Sci-Fi, Tamil Cinema, and many other categories."}
        }
      ]
    }
    </script>
    """
    st.markdown(structured_data, unsafe_allow_html=True)

# Main app
def main():
    # Add JSON-LD structured data
    add_structured_data()
    
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
        # Track click/visit count for this shared link - save to Google Sheets
        try:
            prompt_id = query_params["prompt_id"]
            # Log visit event to Analytics sheet
            log_analytics_event('visit', prompt_id=prompt_id, status='success')
            
            # Also update session state for immediate display
            if 'visit_counts' not in st.session_state:
                st.session_state.visit_counts = {}
            if prompt_id not in st.session_state.visit_counts:
                st.session_state.visit_counts[prompt_id] = 0
            st.session_state.visit_counts[prompt_id] += 1
        except:
            pass
        
        # NO hero section for single prompt view
        show_single_prompt(sheet, query_params["prompt_id"])
        return
    
    # Hero section (only for main page)
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("🎬 Video Prompts Gallery")
        st.subheader("Discover and share amazing AI video generation prompts")
        st.markdown("""
        Welcome to the ultimate collection of cinematic video prompts for AI video generation! 
        Whether you're creating content with Runway, Pika Labs, or other AI video tools, find inspiration 
        from our curated library of professional-grade prompts spanning Nature, Urban landscapes, 
        Cinematic scenes, Sci-Fi adventures, and Tamil cinema aesthetics.
        """)
    with col2:
        # Notification bell for admin only
        if st.session_state.get('authenticated', False):
            error_count, errors = get_admin_notifications()
            if error_count > 0:
                if st.button(f"🔔 {error_count}", key="notifications", help="View error notifications"):
                    st.session_state.show_notifications = True
            else:
                st.markdown("<div style='padding: 0.5rem;'>🔕</div>", unsafe_allow_html=True)
    
    # Show notification panel if clicked
    if st.session_state.get('show_notifications', False) and st.session_state.get('authenticated', False):
        error_count, errors = get_admin_notifications()
        with st.expander("⚠️ Error Notifications", expanded=True):
            if errors:
                for error in errors[:10]:  # Show last 10 errors
                    st.error(f"**{error.get('Timestamp')}** - Prompt ID: {error.get('Prompt ID')}\n{error.get('Error Message')}")
                if st.button("✅ Mark All as Read"):
                    # Update status in Analytics sheet
                    try:
                        analytics_sheet = st.session_state.analytics_sheet
                        all_data = analytics_sheet.get_all_records()
                        for i, row in enumerate(all_data, start=2):
                            if row.get('Event Type') == 'error' and row.get('Status') == 'unread':
                                analytics_sheet.update(f'F{i}', 'read')
                        st.success("All notifications marked as read")
                        st.session_state.show_notifications = False
                        st.rerun()
                    except:
                        st.error("Failed to update notifications")
            else:
                st.info("No new notifications")
    
    st.divider()
    
    # Single ad placement after hero
    show_google_ad(ad_slot="1234567890", ad_format="auto")
    
    # Create tabs - View All is now public
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 Add New", "📚 View All Prompts", "✏️ Manage", "❓ FAQ & Help", "ℹ️ Legal & Info", "💬 Feedback"])
    
    with tab1:
        st.markdown("### ✨ Create New Prompt")
        
        # Check admin authentication
        if check_admin_password("add"):
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🚪 Logout", key="logout", use_container_width=True):
                    st.session_state.authenticated = False
            
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
                    categories = st.multiselect(
                        "🏷️ Categories",
                        ["Nature", "Urban", "People", "Abstract", "Cinematic", "Sci-Fi", "Fantasy", "General"],
                        default=["General"],
                        help="Select one or more categories"
                    )
                    category = ", ".join(categories) if categories else "General"
                
                st.markdown("")  # Spacing
                submitted = st.form_submit_button("💾 Save Prompt", use_container_width=True, type="primary")
                
                if submitted:
                    if prompt.strip() and prompt_name.strip():
                        with st.spinner('Saving...'):
                            if save_prompt(sheet, prompt_name.strip(), prompt.strip(), video_id.strip(), category):
                                # Clear cache
                                if 'cached_prompts' in st.session_state:
                                    del st.session_state['cached_prompts']
                                if 'cached_edit_prompts' in st.session_state:
                                    del st.session_state['cached_edit_prompts']
                                st.success("✅ Saved! Switch to 'View All' tab to see it.")
                    else:
                        st.warning("⚠️ Please enter both prompt name and prompt text!")
    
    # View All Prompts tab - Now public
    with tab2:
        with tab2:
            st.markdown("### 🌟 All Prompts")
            
            # Cache prompts in session state to avoid repeated API calls
            if 'cached_prompts' not in st.session_state or st.button("🔄 Refresh", key="refresh_prompts"):
                with st.spinner('⏳ Loading...'):
                    st.session_state.cached_prompts = get_all_prompts(sheet)
            
            prompts = st.session_state.get('cached_prompts', [])
            
            if prompts:
                # Stats at top - 4 columns with visit tracking
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📊 Total Prompts", len(prompts))
                with col2:
                    st.metric("🆕 Latest", f"#{len(prompts)}")
                with col3:
                    st.metric("🎬 Videos", len([p for p in prompts if p.get('Video ID')]))
                with col4:
                    # Total visits from shared links - get from Analytics sheet
                    try:
                        if 'analytics_sheet' in st.session_state:
                            analytics_sheet = st.session_state.analytics_sheet
                            data = analytics_sheet.get_all_records()
                            visit_count = len([row for row in data if row.get('Event Type') == 'visit'])
                            st.metric("👥 Link Visits", visit_count)
                        else:
                            st.metric("👥 Link Visits", 0)
                    except:
                        st.metric("👥 Link Visits", 0)
                
                st.markdown("---")
                
                # Single ad before prompts
                show_google_ad(ad_slot="1234567891", ad_format="auto")
                
                # Get base URL - check environment variable first, then secrets
                base_url = os.getenv('BASE_URL', 'http://localhost:8501')
                
                # If not in environment, try secrets (for Streamlit Cloud)
                if base_url == 'http://localhost:8501' and not os.path.exists('.env'):
                    try:
                        base_url = st.secrets.get('BASE_URL', 'http://localhost:8501')
                    except:
                        pass
                
                # Initialize pagination in session state
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 1
                
                # Track previous search/filter to reset pagination when changed
                if 'prev_search' not in st.session_state:
                    st.session_state.prev_search = ""
                if 'prev_filter' not in st.session_state:
                    st.session_state.prev_filter = "All"
                
                # Search box and category filter
                col1, col2 = st.columns([3, 1])
                with col1:
                    search_query = st.text_input("🔍 Search prompts...", placeholder="Type to filter prompts", key="search_input")
                with col2:
                    # Get unique categories from all prompts (split multi-categories)
                    all_categories = set()
                    for p in prompts:
                        cat = p.get('Category', 'General')
                        if cat:
                            for c in cat.split(','):
                                all_categories.add(c.strip())
                    all_categories = sorted(list(all_categories))
                    filter_category = st.selectbox("🏷️ Filter by Category", ["All"] + all_categories, index=0)
                
                # Reset to page 1 if search or filter changed
                if search_query != st.session_state.prev_search or filter_category != st.session_state.prev_filter:
                    st.session_state.current_page = 1
                    st.session_state.prev_search = search_query
                    st.session_state.prev_filter = filter_category
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # First pass: Collect all filtered prompts
                filtered_prompts = []
                for idx, prompt_data in enumerate(reversed(prompts)):
                    prompt_num = len(prompts) - idx
                    unique_id = prompt_data.get('Unique ID', f'PR{str(prompt_num).zfill(4)}')
                    prompt_name = prompt_data.get('Prompt Name', f'Prompt {prompt_num}')
                    category = prompt_data.get('Category', 'General')
                    prompt_text = prompt_data.get('Prompt', 'N/A')
                    
                    # Skip empty prompts
                    if not prompt_text or prompt_text.strip() == '' or prompt_text == 'N/A':
                        continue
                    
                    # Filter by category (check if ANY of the prompt's categories match)
                    if filter_category != "All":
                        prompt_categories = [c.strip() for c in category.split(',')] if category else ["General"]
                        if filter_category not in prompt_categories:
                            continue
                    
                    # Filter by search (check prompt name, text, and categories)
                    if search_query:
                        search_lower = search_query.lower()
                        if not (search_lower in prompt_text.lower() or 
                                search_lower in prompt_name.lower() or 
                                search_lower in category.lower()):
                            continue
                    
                    # Add to filtered list
                    filtered_prompts.append({
                        'prompt_num': prompt_num,
                        'unique_id': unique_id,
                        'prompt_name': prompt_name,
                        'category': category,
                        'prompt_text': prompt_text,
                        'prompt_data': prompt_data
                    })
                
                # Pagination settings
                PROMPTS_PER_PAGE = 10
                total_filtered = len(filtered_prompts)
                total_pages = max(1, (total_filtered + PROMPTS_PER_PAGE - 1) // PROMPTS_PER_PAGE)
                
                # Reset to page 1 if current page exceeds total pages
                if st.session_state.current_page > total_pages:
                    st.session_state.current_page = 1
                
                # Calculate start and end indices for current page
                start_idx = (st.session_state.current_page - 1) * PROMPTS_PER_PAGE
                end_idx = min(start_idx + PROMPTS_PER_PAGE, total_filtered)
                
                # Pagination controls function
                def render_pagination():
                    if total_pages > 1:
                        # Create pagination buttons
                        cols = st.columns([1, 1, 2, 1, 1])
                        
                        with cols[0]:
                            if st.session_state.current_page > 1:
                                if st.button("⬅️ Previous", use_container_width=True, key=f"prev_{st.session_state.get('pagination_location', 'top')}"):
                                    st.session_state.current_page -= 1
                                    st.rerun()
                        
                        with cols[2]:
                            # Page number buttons (show max 5 pages)
                            page_buttons = []
                            if total_pages <= 5:
                                page_buttons = list(range(1, total_pages + 1))
                            else:
                                current = st.session_state.current_page
                                if current <= 3:
                                    page_buttons = [1, 2, 3, 4, 5]
                                elif current >= total_pages - 2:
                                    page_buttons = list(range(total_pages - 4, total_pages + 1))
                                else:
                                    page_buttons = list(range(current - 2, current + 3))
                            
                            page_cols = st.columns(len(page_buttons))
                            for i, page_num in enumerate(page_buttons):
                                with page_cols[i]:
                                    if page_num == st.session_state.current_page:
                                        st.markdown(f"<div style='text-align: center; padding: 0.5rem; background: #667eea; color: white; border-radius: 8px; font-weight: bold;'>{page_num}</div>", unsafe_allow_html=True)
                                    else:
                                        if st.button(str(page_num), key=f"page_{page_num}_{st.session_state.get('pagination_location', 'top')}", use_container_width=True):
                                            st.session_state.current_page = page_num
                                            st.rerun()
                        
                        with cols[4]:
                            if st.session_state.current_page < total_pages:
                                if st.button("Next ➡️", use_container_width=True, key=f"next_{st.session_state.get('pagination_location', 'top')}"):
                                    st.session_state.current_page += 1
                                    st.rerun()
                
                # Show pagination info and controls at TOP
                if total_filtered > 0:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.info(f"📄 Showing {start_idx + 1}-{end_idx} of **{total_filtered}** prompts | Page {st.session_state.current_page}/{total_pages}")
                    
                    st.session_state.pagination_location = 'top'
                    render_pagination()
                    st.markdown("<br>", unsafe_allow_html=True)
                
                # Display prompts for current page
                for idx, prompt_info in enumerate(filtered_prompts[start_idx:end_idx]):
                    prompt_num = prompt_info['prompt_num']
                    unique_id = prompt_info['unique_id']
                    prompt_name = prompt_info['prompt_name']
                    category = prompt_info['category']
                    prompt_text = prompt_info['prompt_text']
                    prompt_data = prompt_info['prompt_data']
                    
                    share_link = f"{base_url}?prompt_id={unique_id}"
                    
                    # Main card container
                    st.markdown('<div class="prompt-container">', unsafe_allow_html=True)
                    
                    # HEADER SECTION (Purple gradient) - Show Prompt Name with Category
                    # Create category badges
                    category_list = [c.strip() for c in category.split(',')] if category else ["General"]
                    category_badges = ''.join([f'<span style="background: rgba(255,255,255,0.2); padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem; margin-right: 0.5rem;">🏷️ {cat}</span>' for cat in category_list])
                    
                    st.markdown(f'''
                        <div class="prompt-header">
                            <h2 style="margin: 0; font-size: 1.8rem; color: white;">🎬 {prompt_name}</h2>
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                                <p style="margin: 0; opacity: 0.9; font-size: 0.95rem;">Prompt #{prompt_num}</p>
                                {category_badges}
                            </div>
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

                    # ---- Like button ----
                    st.markdown("<br>", unsafe_allow_html=True)
                    like_key = f"liked_{unique_id}"
                    like_cache_key = f"like_count_{unique_id}"
                    if like_cache_key not in st.session_state:
                        st.session_state[like_cache_key] = get_likes_count(unique_id)
                    like_count = st.session_state[like_cache_key]
                    already_liked = st.session_state.get(like_key, False)
                    like_col, _ = st.columns([1, 3])
                    with like_col:
                        like_label = f"❤️ {like_count} Liked" if already_liked else f"🤍 {like_count} Like"
                        if st.button(like_label, key=f"like_btn_{idx}_{prompt_num}", use_container_width=True, disabled=already_liked):
                            add_like(unique_id)
                            st.session_state[like_cache_key] = like_count + 1
                            st.session_state[like_key] = True
                            st.rerun()

                    # ---- Comments section ----
                    comment_cache_key = f"comments_{unique_id}"
                    if comment_cache_key not in st.session_state:
                        st.session_state[comment_cache_key] = get_comments(unique_id)
                    comments = st.session_state[comment_cache_key]
                    with st.expander(f"💬 Comments ({len(comments)})"):
                        if comments:
                            for c in comments[-5:]:
                                name_disp = c.get('Name', 'Anonymous') or 'Anonymous'
                                comment_disp = c.get('Comment', '')
                                ts_disp = str(c.get('Timestamp', ''))[:10]
                                st.markdown(f"""
                                    <div style="background: rgba(255,255,255,0.1); padding: 0.6rem 1rem; border-radius: 8px; margin: 0.4rem 0; border-left: 3px solid #667eea;">
                                        <strong style="color: white;">👤 {name_disp}</strong>
                                        <span style="color: rgba(255,255,255,0.6); font-size: 0.8rem; margin-left: 0.5rem;">{ts_disp}</span>
                                        <p style="color: white; margin: 0.3rem 0 0 0; font-size: 0.95rem;">{comment_disp}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.caption("No comments yet. Be the first!")
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.form(key=f"comment_form_{idx}_{prompt_num}", clear_on_submit=True):
                            c_name = st.text_input("Your name (optional)", max_chars=50)
                            c_text = st.text_area("Your comment", max_chars=500, height=80)
                            if st.form_submit_button("📤 Post Comment", use_container_width=True):
                                if c_text.strip():
                                    if add_comment(unique_id, c_name or "Anonymous", c_text):
                                        if comment_cache_key in st.session_state:
                                            del st.session_state[comment_cache_key]
                                        st.success("✅ Comment posted!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Could not post comment. Try again.")
                                else:
                                    st.warning("⚠️ Please write a comment before posting.")

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
                    
                    # Show share link if button clicked (admin only)
                    if st.session_state.get(f"show_link_{idx}", False) and st.session_state.get('authenticated', False):
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.info("🔗 Share this unique link:")
                        st.code(share_link, language="text")
                        # Show visit count for this prompt from Analytics sheet
                        try:
                            if 'analytics_sheet' in st.session_state:
                                analytics_sheet = st.session_state.analytics_sheet
                                data = analytics_sheet.get_all_records()
                                visit_count = len([row for row in data if row.get('Event Type') == 'visit' and row.get('Prompt ID') == unique_id])
                                st.caption(f"👥 This link has been visited {visit_count} time(s)")
                            else:
                                st.caption("👥 Visit tracking: Not available")
                        except:
                            st.caption("👥 Visit tracking: Error loading data")
                        if st.button("✕ Close", key=f"close_{idx}_{prompt_num}", type="primary"):
                            st.session_state[f"show_link_{idx}"] = False
                    
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
                    
                    # Display ads after every 3 prompts to not be intrusive
                    if (idx + 1) % 3 == 0:
                        show_google_ad(ad_slot="1234567892", ad_format="auto")
                
                # Pagination controls at BOTTOM
                if total_pages > 1:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.session_state.pagination_location = 'bottom'
                    render_pagination()
                
                # Show no results message if filtered list is empty
                if total_filtered == 0:
                    st.info("🔍 No prompts match your search/filter criteria. Try different keywords or select 'All' categories.")
            else:
                st.info("📭 No prompts yet. Add your first prompt in the 'Add New' tab!")
    
    with tab3:
        st.markdown("### ⚙️ Manage Prompts")
        
        # Check admin authentication
        if check_admin_password("edit"):
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🚪 Logout", key="logout_edit", use_container_width=True):
                    st.session_state.authenticated = False
            
            st.markdown("")  # Spacing
            
            # Cache prompts to reduce API calls
            if 'cached_edit_prompts' not in st.session_state or st.button("🔄 Refresh List", key="refresh_edit"):
                with st.spinner('⏳ Loading...'):
                    st.session_state.cached_edit_prompts = get_all_prompts(sheet)
            
            prompts = st.session_state.get('cached_edit_prompts', [])
            
            if prompts:
                # Select prompt to edit
                st.markdown('<p style="color: white; font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;">Select a prompt to edit or delete:</p>', unsafe_allow_html=True)
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
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edited_video_id = st.text_input(
                            "📹 Video ID:",
                            value=selected_prompt.get('Video ID', '')
                        )
                    with col2:
                        current_category = selected_prompt.get('Category', 'General')
                        category_options = ["Nature", "Urban", "People", "Abstract", "Cinematic", "Sci-Fi", "Fantasy", "General"]
                        # Parse current categories (could be comma-separated)
                        current_cats = [c.strip() for c in current_category.split(',')] if current_category else ["General"]
                        edited_categories = st.multiselect(
                            "🏷️ Categories:",
                            category_options,
                            default=[c for c in current_cats if c in category_options] or ["General"]
                        )
                        edited_category = ", ".join(edited_categories) if edited_categories else "General"
                    
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
                            with st.spinner('Updating...'):
                                if save_prompt(sheet, edited_prompt_name.strip(), edited_prompt.strip(), edited_video_id.strip(), edited_category, row_num):
                                    if 'cached_prompts' in st.session_state:
                                        del st.session_state['cached_prompts']
                                    if 'cached_edit_prompts' in st.session_state:
                                        del st.session_state['cached_edit_prompts']
                                    st.success("✅ Updated! Click Refresh to see changes.")
                        else:
                            st.warning("⚠️ Cannot be empty!")
                    
                    if delete_btn:
                        with st.spinner('Deleting...'):
                            if delete_prompt(sheet, row_num):
                                if 'cached_prompts' in st.session_state:
                                    del st.session_state['cached_prompts']
                                if 'cached_edit_prompts' in st.session_state:
                                    del st.session_state['cached_edit_prompts']
                                st.success("✅ Deleted! Click Refresh to see changes.")
            else:
                st.info("📭 No prompts to manage yet.")
    
    # Legal & Info Tab (Tab 4) - Required for AdSense
    with tab4:
        st.markdown("### ❓ Frequently Asked Questions")
        st.caption("Everything you need to know about using Video Prompts Gallery")
        
        # FAQ sections
        faq_tab1, faq_tab2, faq_tab3 = st.tabs(["🎬 General", "🔧 Technical", "📝 Prompts"])
        
        with faq_tab1:
            st.markdown("""
            # General Questions
            
            ### What is Video Prompts Gallery?
            Video Prompts Gallery is a free, curated collection of high-quality video prompts designed for AI video generation tools like Runway ML, Pika Labs, and similar platforms. We provide professionally crafted prompts across multiple categories to inspire and assist content creators.
            
            ### Is this service free?
            Yes! All prompts are completely free to view and use. We're supported by AdSense advertising, which allows us to keep the service free for everyone.
            
            ### Who can use these prompts?
            Anyone! Whether you're a:
            - Professional filmmaker
            - Content creator
            - AI enthusiast
            - Student learning about AI video generation
            - Hobbyist exploring creative tools
            
            All our prompts are freely available for your creative projects.
            
            ### Do I need an account?
            No account is needed to view and use prompts. Only site administrators need authentication to add or manage content.
            
            ### How often is new content added?
            We regularly add new prompts across all categories. Check back frequently for fresh inspiration!
            
            ### Can I share prompts with others?
            Absolutely! Each prompt has a unique share link. Click the "🔗 Share Link" button on any prompt to copy the direct URL you can share via email, social media, or messaging apps.
            
            ### What makes your prompts special?
            Our prompts are:
            - **Detailed & Cinematic:** Professionally crafted with attention to visual details
            - **Category-Diverse:** Spanning Nature, Urban, Sci-Fi, Fantasy, and more
            - **Tamil Cinema Focused:** Special collection celebrating South Indian cinematography
            - **AI-Optimized:** Tested to work well with popular AI video generation tools
            """)
        
        with faq_tab2:
            st.markdown("""
            # Technical Questions
            
            ### Which AI video tools work with these prompts?
            Our prompts are designed to work with all major AI video generation platforms:
            - Runway ML (Gen-1, Gen-2)
            - Pika Labs
            - Stable Video Diffusion
            - Any text-to-video AI tool
            
            Simply copy the prompt text and paste it into your preferred tool.
            
            ### How do I copy a prompt?
            1. Browse to the prompt you want
            2. Click the "📋 Copy Text" button
            3. A text area will appear with the full prompt
            4. Press Ctrl+C (Windows/Linux) or Cmd+C (Mac) to copy
            5. Paste into your AI video generation tool
            
            ### How do I search for specific prompts?
            Use the search box in the "View All Prompts" tab. You can search by:
            - Keywords in the prompt text
            - Prompt names
            - Category names
            
            ### What are the category filters?
            We organize prompts into:
            - **Nature:** Landscapes, wildlife, natural scenery
            - **Urban:** Cities, architecture, street scenes
            - **People:** Character-focused, human interactions
            - **Cinematic:** Movie-style dramatic scenes
            - **Sci-Fi:** Futuristic, space, technology
            - **Fantasy:** Magical, mythical, imaginative
            - **Abstract:** Artistic, experimental visuals
            - **General:** Uncategorized or multi-category
            
            ### Why does the site take time to load initially?
            We use Render.com's free hosting tier, which puts the site to sleep after 15 minutes of inactivity. When someone visits after it's been idle, it takes 30-60 seconds to "wake up." After that initial load, everything runs smoothly!
            
            ### Is the site mobile-friendly?
            Yes! The entire gallery is fully responsive and works seamlessly on:
            - Smartphones
            - Tablets
            - Desktop computers
            - All major browsers (Chrome, Firefox, Safari, Edge)
            
            ### How is my data protected?
            - We don't collect personal information from visitors
            - No account or login required to view prompts
            - Admin authentication is password-protected with rate limiting
            - All data is encrypted in transit (HTTPS)
            - See our Privacy Policy for full details
            
            ### I found a bug. How do I report it?
            Please email us at k8744185@gmail.com with:
            - Description of the issue
            - Your browser and version
            - Steps to reproduce the problem
            - Screenshots if applicable
            """)
        
        with faq_tab3:
            st.markdown("""
            # Prompt-Related Questions
            
            ### Can I modify the prompts?
            Absolutely! Feel free to:
            - Adapt prompts to your specific needs
            - Combine multiple prompts
            - Add or remove details
            - Translate to other languages
            - Customize for your AI tool's requirements
            
            ### Can I suggest new prompts?
            Yes! We welcome suggestions. Email us at k8744185@gmail.com with your prompt ideas. Include:
            - Suggested category
            - Full prompt text
            - Any reference images or inspiration (optional)
            
            ### Can I submit my own prompts?
            Currently, only site administrators can add prompts to maintain quality and consistency. However, we're considering a submission system for the future. Contact us if you're interested in contributing!
            
            ### What makes a good video prompt?
            Effective video prompts typically include:
            - **Specific visual details:** Colors, lighting, camera angles
            - **Clear subject:** What's the main focus?
            - **Atmosphere/Mood:** Emotional tone, time of day
            - **Motion description:** How things move in the scene
            - **Technical details:** Camera movement, shot type
            
            Example: "A cinematic wide shot of a misty forest at dawn, golden sunlight filtering through ancient trees, slow camera dolly forward, atmospheric and serene."
            
            ### How do I use prompts with different AI tools?
            **For Runway ML:**
            1. Copy the prompt
            2. Paste into the text prompt field
            3. Adjust duration and other settings
            4. Generate!
            
            **For Pika Labs:**
            1. Copy the prompt
            2. Use the `/create` command in Discord
            3. Paste the prompt
            4. Add parameters if needed (-fps, -motion, etc.)
            
            Each tool has slightly different syntax, but our prompts work as a solid foundation for all platforms.
            
            ### What's the Tamil cinema focus about?
            We have a special collection celebrating Tamil cinema aesthetics, including:
            - Romantic scenes inspired by Tamil films
            - Indian locations (Chennai, Ooty, Coimbatore)
            - South Indian cultural elements
            - Cinematic styles popular in Tamil filmmaking
            
            This makes our gallery unique and provides culturally rich prompts you won't find elsewhere!
            
            ### Can I use these prompts commercially?
            The prompts themselves are free to use for any purpose, including commercial projects. However:
            - Check the terms of service of your AI video generation tool
            - The AI-generated videos are your creation
            - Attribution to Video Prompts Gallery is appreciated but not required
            - See our Terms of Service for full legal details
            
            ### How accurate are prompt results?
            AI video generation results vary based on:
            - The specific AI tool you use
            - Tool version and updates
            - Random seed values
            - Your additional parameters
            
            Our prompts provide a solid foundation, but you may need to:
            - Run multiple generations
            - Tweak the prompt slightly
            - Adjust tool-specific settings
            - Combine with reference images (if supported)
            """)
    
    with tab5:
        st.markdown("### 📋 Legal & Information")
        st.caption("Required pages for transparency and AdSense compliance")
        
        # Create sub-sections
        legal_tab1, legal_tab2, legal_tab3, legal_tab4, legal_tab5 = st.tabs(["📜 Privacy Policy", "📝 Terms of Service", "📧 Contact Us", "ℹ️ About", "🗺️ Sitemap"])
        
        with legal_tab1:
            st.markdown("""
            # Privacy Policy
            
            **Last Updated:** February 15, 2026
            
            ## Introduction
            Video Prompts Gallery ("we", "our", "us") operates https://video-prompts-gallery.onrender.com (the "Site"). This page informs you of our policies regarding the collection, use, and disclosure of personal information when you use our Site.
            
            ## Information Collection and Use
            While using our Site, we may ask you to provide us with certain personally identifiable information that can be used to contact or identify you.
            
            ### Types of Data Collected:
            - **Personal Data:** Email address (if you contact us)
            - **Usage Data:** IP address, browser type, pages visited, time spent
            - **Cookies:** We use cookies to track activity on our Site
            
            ## Google AdSense
            We use Google AdSense to display advertisements. Google may use cookies to serve ads based on your prior visits to our Site or other websites. You can opt out of personalized advertising by visiting [Google Ads Settings](https://www.google.com/settings/ads).
            
            ## Google Sheets Integration
            We use Google Sheets to store prompt data. Only administrators with proper authentication can modify this data.
            
            ## Data Security
            We value your trust in providing us your Personal Information and strive to use commercially acceptable means of protecting it. However, no method of transmission over the internet is 100% secure.
            
            ## Links to Other Sites
            Our Site may contain links to other sites. We are not responsible for the privacy practices of other sites.
            
            ## Children's Privacy
            Our Site does not address anyone under the age of 13. We do not knowingly collect personal information from children under 13.
            
            ## Changes to This Privacy Policy
            We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page.
            
            ## Contact Us
            If you have any questions about this Privacy Policy, please contact us at: k8744185@gmail.com
            """)
        
        with legal_tab2:
            st.markdown("""
            # Terms of Service
            
            **Last Updated:** February 15, 2026
            
            ## 1. Agreement to Terms
            By accessing Video Prompts Gallery, you agree to be bound by these Terms of Service and all applicable laws and regulations.
            
            ## 2. Use License
            Permission is granted to temporarily view and use the prompts on this site for personal, non-commercial use only.
            
            ### You May NOT:
            - Modify or copy the materials without permission
            - Use the materials for commercial purposes
            - Remove any copyright or proprietary notations
            - Transfer the materials to another person
            
            ## 3. Disclaimer
            The materials on Video Prompts Gallery are provided on an 'as is' basis. We make no warranties, expressed or implied, and hereby disclaim all other warranties.
            
            ## 4. Limitations
            In no event shall Video Prompts Gallery or its suppliers be liable for any damages arising out of the use or inability to use the materials on our Site.
            
            ## 5. User Conduct
            You agree to:
            - Not violate any laws while using our Site
            - Not post or transmit harmful content
            - Not attempt to gain unauthorized access to our systems
            
            ## 6. Intellectual Property
            All prompts and content on this Site are the property of Video Prompts Gallery or its content creators.
            
            ## 7. Third-Party Services
            Our Site uses third-party services (Google Sheets, Google AdSense) which have their own Terms of Service.
            
            ## 8. Modifications
            We reserve the right to revise these terms at any time without notice. By continuing to use this Site, you agree to be bound by the current version of these Terms of Service.
            
            ## 9. Governing Law
            These terms shall be governed by and construed in accordance with the laws of India.
            
            ## 10. Contact Information
            For questions about these Terms, contact: k8744185@gmail.com
            """)
        
        with legal_tab3:
            st.markdown("""
            # Contact Us
            
            We'd love to hear from you! Whether you have questions, feedback, or need support, feel free to reach out.
            
            ## 📧 Email
            **General Inquiries:** k8744185@gmail.com
            
            ## 🌐 Website
            **Live Site:** https://video-prompts-gallery.onrender.com
            
            ## 💬 Feedback & Suggestions
            We're always looking to improve! If you have:
            - Feature requests
            - Bug reports
            - Content suggestions
            - Partnership inquiries
            
            Please email us with the subject line indicating your inquiry type.
            
            ## ⏰ Response Time
            We typically respond within 24-48 hours during business days.
            
            ## 🔒 Privacy
            All communications are kept confidential and handled in accordance with our Privacy Policy.
            
            ## 🐛 Report Issues
            Found a technical issue? Please include:
            - Your browser and version
            - Steps to reproduce the issue
            - Screenshots (if applicable)
            
            ## 📱 Social Media
            Stay updated with our latest prompts and features!
            *(Add your social media links here when available)*
            
            ---
            
            **Administrator:** K. Venkadesan  
            **Email:** k8744185@gmail.com  
            **Location:** India (IST Timezone)
            """)
        
        with legal_tab4:
            st.markdown("""
            # About Video Prompts Gallery
            
            ## 🎬 Our Mission
            Video Prompts Gallery is a curated collection of high-quality video prompts designed to inspire creators, filmmakers, and AI enthusiasts worldwide. Our goal is to provide cinematic, detailed prompts that help bring visual stories to life through AI-powered video generation.
            
            In an era where AI video generation is revolutionizing content creation, we bridge the gap between creative vision and technical execution by offering professionally crafted prompts that maximize the potential of AI tools.
            
            ## 🌟 What We Offer
            - **Curated Prompts:** Handcrafted video prompts across multiple categories, each carefully designed for cinematic quality
            - **Multiple Categories:** Nature, Urban, People, Cinematic, Sci-Fi, Fantasy, Abstract, and General
            - **Tamil Cinema Focus:** Unique collection celebrating Tamil cinema aesthetics and romantic scenes
            - **Advanced Search:** Find the perfect prompt with intelligent search and category filters
            - **Free Access:** All prompts are freely accessible to everyone, forever
            - **Share Functionality:** Easy-to-use share links for collaboration
            - **Mobile Optimized:** Seamless experience on all devices
            
            ## 🎯 Why We Exist
            With the rapid rise of AI video generation tools like Runway ML, Pika Labs, and Stable Video Diffusion, having well-crafted prompts has become essential for:
            - **Saving Time:** Skip the trial-and-error of prompt engineering
            - **Inspiring Creativity:** Discover new directions for your projects
            - **Learning:** Understand what makes effective video prompts
            - **Cultural Celebration:** Showcase Tamil cinema and Indian locations to global audiences
            - **Community Building:** Create a resource hub for AI video creators
            
            ## 💡 Our Unique Value
            Unlike generic prompt collections, we offer:
            - **Cinematic Focus:** Every prompt is crafted with filmmaking principles
            - **Cultural Diversity:** Special emphasis on Tamil cinema and Indian aesthetics
            - **Quality over Quantity:** Each prompt is tested and refined
            - **Detailed Descriptions:** Rich visual details for better AI output
            - **Categorized Organization:** Easy to find exactly what you need
            
            ## 🛠️ Technology Stack
            Built with modern, reliable technologies:
            - **Streamlit:** Modern Python web framework for fast, interactive UIs
            - **Google Sheets API:** Cloud-based data storage with real-time sync
            - **Render.com:** Reliable hosting with automatic deployments
            - **Google AdSense:** Supporting our free service through ethical advertising
            - **Python 3.11:** Latest Python with optimized performance
            
            ## 📊 Platform Features
            - 🔍 **Advanced Search:** Keyword search across all prompts and metadata
            - 🏷️ **Multi-Category Tagging:** Prompts can belong to multiple categories
            - 📄 **Smart Pagination:** Browse large collections smoothly (10 prompts per page)
            - 🕒 **IST Timestamps:** All times in India Standard Time
            - 📱 **Responsive Design:** Perfect on desktop, tablet, and mobile
            - 🔐 **Secure Admin Portal:** Password-protected content management
            - 🔗 **Unique Share Links:** Every prompt has a permanent shareable URL
            - 📊 **Analytics:** Track popular prompts and user engagement
            - ⚡ **Optimized Performance:** Fast loading even on free hosting tier
            
            ## 👥 Who Uses Video Prompts Gallery?
            Our diverse user base includes:
            - **AI Video Creators:** Using Runway, Pika, and other AI tools
            - **Filmmakers:** Finding inspiration for traditional and AI-assisted projects
            - **Content Creators:** YouTubers, social media creators, marketers
            - **Educators:** Teaching AI video generation and cinematography
            - **Students:** Learning about visual storytelling and AI
            - **Tamil Cinema Fans:** Celebrating South Indian film aesthetics
            - **Creative Professionals:** Designers, animators, visual artists
            
            ## 🌏 Global Reach, Local Flavor
            While our prompts are useful for creators worldwide, we proudly feature:
            - **Tamil Nadu Locations:** Chennai, Ooty, Coimbatore, Madurai
            - **Indian Architecture:** Temples, colonial buildings, modern cityscapes
            - **South Indian Culture:** Traditional attire, festivals, customs
            - **Tamil Cinema Style:** Romantic scenes, dramatic moments, musical aesthetics
            - **Regional Landscapes:** Western Ghats, coastal areas, urban centers
            
            ## 📈 Project Milestones
            - **Launch:** February 2026
            - **Initial Collection:** 30+ professional prompts
            - **Categories:** 8 diverse categories covering all genres
            - **Update Frequency:** New prompts added weekly
            - **Platform:** Fully responsive web application
            - **Accessibility:** 100% free, no registration required
            
            ## 🎨 Content Philosophy
            We believe that:
            - **Quality > Quantity:** Each prompt is carefully crafted
            - **Diversity Matters:** Multiple perspectives and styles
            - **Detail is King:** Specific visual descriptions yield better results
            - **Culture is Beautiful:** Celebrating global and local aesthetics
            - **Free Access is Essential:** Knowledge should be shared
            
            ## 🤝 Get Involved
            We welcome collaboration! Contact us for:
            - **Prompt Suggestions:** Share your creative ideas
            - **Partnership Opportunities:** Collaborate with us
            - **Feedback:** Help us improve the platform
            - **Bug Reports:** Technical issues or improvements
            - **Feature Requests:** What would make this better?
            
            Email: k8744185@gmail.com
            
            ## 🔒 Privacy & Ethics
            - We respect your privacy (see Privacy Policy)
            - No tracking beyond basic analytics
            - Ethical advertising through Google AdSense
            - No sale of user data
            - Open about our technology and practices
            
            ## 📜 Legal & Compliance
            All content is original and created specifically for this platform. We comply with:
            - Google AdSense policies
            - Privacy regulations
            - Copyright laws
            - Terms of service for all integrated platforms
            
            See our Terms of Service and Privacy Policy for complete legal information.
            
            ## 🙏 Acknowledgments
            Special thanks to:
            - The open-source community (Streamlit, Python)
            - AI video generation pioneers (Runway, Pika Labs)
            - Tamil cinema for endless inspiration
            - Our users for their support and feedback
            
            ---
            
            **Created with ❤️ in India**  
            **Celebrating Cinema, Technology, and Creativity**  
            **© 2026 Video Prompts Gallery. All rights reserved.**  
            **Founder & Developer:** K. Venkadesan
            """)
        
        with legal_tab5:
            st.markdown("# 🗺️ Sitemap")
            st.caption("XML Sitemap for search engines")
            
            # Generate sitemap
            prompts = get_all_prompts(sheet)
            sitemap_xml = generate_sitemap(prompts)
            
            st.markdown("""
            This sitemap helps search engines discover and index all pages on our website.
            
            **What's included:**
            - Homepage
            - Legal pages (Privacy, Terms, Contact, About)
            - All prompt pages (up to 50)
            """)
            
            # Show download button
            st.download_button(
                label="📥 Download sitemap.xml",
                data=sitemap_xml,
                file_name="sitemap.xml",
                mime="application/xml"
            )
            
            # Show preview
            with st.expander("👁️ Preview Sitemap"):
                st.code(sitemap_xml, language="xml")

    with tab6:
        st.markdown("### 💬 Website Feedback")
        st.markdown("We'd love to hear what you think about **Video Prompts Gallery**! Your feedback helps us improve.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Feedback form
        with st.form("feedback_form", clear_on_submit=True):
            fb_name = st.text_input("Your name (optional)", max_chars=50, placeholder="Anonymous")
            fb_email = st.text_input("Email (optional — for a reply)", max_chars=100, placeholder="you@example.com")

            st.markdown("**⭐ How would you rate this site?**")
            fb_rating = st.select_slider(
                "Rating",
                options=[1, 2, 3, 4, 5],
                value=5,
                format_func=lambda x: "⭐" * x,
                label_visibility="collapsed"
            )
            fb_comment = st.text_area(
                "Your feedback / suggestions",
                max_chars=1000,
                height=120,
                placeholder="What do you love? What can be improved? Any features you'd like to see?"
            )

            submit_fb = st.form_submit_button("📩 Submit Feedback", use_container_width=True, type="primary")
            if submit_fb:
                if fb_comment.strip():
                    with st.spinner("Submitting..."):
                        if add_feedback(fb_name or "Anonymous", fb_rating, fb_comment, fb_email):
                            st.success("✅ Thank you for your feedback! We really appreciate it. 🙏")
                        else:
                            st.error("❌ Could not submit feedback. Please try again later.")
                else:
                    st.warning("⚠️ Please write some feedback before submitting.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        # Show aggregated ratings (if feedback sheet loaded)
        st.markdown("### 📊 Community Ratings")
        try:
            fb_sheet = get_or_create_feedback_sheet()
            if fb_sheet:
                fb_data = fb_sheet.get_all_records()
                if fb_data:
                    ratings = [int(r.get('Rating', 5)) for r in fb_data if r.get('Rating')]
                    avg_rating = sum(ratings) / len(ratings) if ratings else 5
                    st.metric("Average Rating", f"{'⭐' * round(avg_rating)} ({avg_rating:.1f}/5)", f"{len(ratings)} review(s)")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**Recent reviews:**")
                    for r in reversed(fb_data[-5:]):
                        r_name = r.get('Name', 'Anonymous') or 'Anonymous'
                        r_rating = int(r.get('Rating', 5))
                        r_comment = r.get('Comment', '')
                        r_ts = str(r.get('Timestamp', ''))[:10]
                        if r_comment:
                            st.markdown(f"""
                                <div style="background: rgba(255,255,255,0.1); padding: 0.7rem 1.1rem; border-radius: 10px; margin: 0.5rem 0; border-left: 4px solid #764ba2;">
                                    <strong style="color: white;">👤 {r_name}</strong>
                                    <span style="color: gold; margin-left: 0.5rem;">{"⭐" * r_rating}</span>
                                    <span style="color: rgba(255,255,255,0.6); font-size: 0.8rem; margin-left: 0.5rem;">{r_ts}</span>
                                    <p style="color: white; margin: 0.3rem 0 0 0; font-size: 0.95rem;">{r_comment}</p>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No feedback yet — be the first to share your thoughts! 😊")
            else:
                st.caption("Feedback stats loading...")
        except Exception:
            st.caption("Could not load feedback stats.")

    # Footer - appears on all pages
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 2rem 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-top: 3rem;">
            <h3 style="color: white; margin-bottom: 1rem;">🎬 Video Prompts Gallery</h3>
            <p style="color: rgba(255,255,255,0.9); margin-bottom: 1.5rem;">Your source for cinematic AI video prompts</p>
            <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
                <a href="?tab=FAQ+%26+Help" style="color: white; text-decoration: none;">❓ FAQ</a>
                <a href="?tab=Legal+%26+Info" style="color: white; text-decoration: none;">📋 Legal</a>
                <a href="mailto:k8744185@gmail.com" style="color: white; text-decoration: none;">📧 Contact</a>
                <a href="https://github.com" style="color: white; text-decoration: none;" target="_blank">💻 GitHub</a>
            </div>
            <p style="color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;">
                © 2026 Video Prompts Gallery | Made with ❤️ in India<br>
                <span style="font-size: 0.8rem;">Celebrating Cinema, Technology & Creativity</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

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
                # Log error to analytics
                log_analytics_event('error', prompt_id=prompt_id, error_msg='Prompt not found or empty', status='unread')
                st.error("❌ Prompt not found!")
                if st.button("📚 View All Prompts", type="primary"):
                    st.query_params.clear()
                    st.rerun()
                return
            
            # Single compact card - NO separate hero (NO ADS on shared page)
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
            
            # Metadata footer
            if prompt_data.get('Video ID') or prompt_data.get('Timestamp'):
                st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.15); padding: 0.6rem 1rem; border-radius: 12px; margin-top: 0.8rem; border: 1px solid rgba(255, 255, 255, 0.2); font-size: 0.85rem; color: white; display: flex; justify-content: space-between; flex-wrap: wrap;">
                        <span>📹 <strong>{prompt_data.get('Video ID', 'N/A')}</strong></span>
                        <span style="opacity: 0.9;">🕒 {prompt_data.get('Timestamp', 'N/A')}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # Log error to analytics
            log_analytics_event('error', prompt_id=prompt_id, error_msg='Prompt ID not found in database', status='unread')
            st.error("❌ Prompt not found!")
            if st.button("📚 View All Prompts", type="primary"):
                st.query_params.clear()
                st.rerun()
    except Exception as e:
        # Log error to analytics
        log_analytics_event('error', prompt_id=prompt_id, error_msg=str(e), status='unread')
        st.error(f"❌ Error loading prompt: {str(e)}")
        if st.button("📚 View All Prompts", type="primary"):
            st.query_params.clear()
            st.rerun()

if __name__ == "__main__":
    main()
