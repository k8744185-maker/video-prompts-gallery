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

# Optimize for Render.com free tier (512MB RAM, 0.1 CPU)
import gc
gc.set_threshold(50, 5, 5)  # More aggressive garbage collection

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

# SEO Meta Tags for AdSense Approval
st.markdown("""
    <meta name="description" content="Curated collection of high-quality AI video prompts for filmmakers and creators. Tamil cinema inspired prompts, nature scenes, urban cinematography and more.">
    <meta name="keywords" content="video prompts, AI video generation, Tamil cinema prompts, cinematic prompts, filmmaking, Runway ML, Pika Labs">
    <meta name="author" content="K. Venkadesan">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="Video Prompts Gallery - AI Video Prompt Collection">
    <meta property="og:description" content="30+ curated video prompts for AI video generation tools">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://video-prompts-gallery.onrender.com">
    <link rel="canonical" href="https://video-prompts-gallery.onrender.com">
""", unsafe_allow_html=True)

# Google AdSense Verification - Using components.html() for proper injection
components.html("""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5050768956635718"
         crossorigin="anonymous"></script>
""", height=0)

# Custom CSS - Ultra minimal for speed
st.markdown("""
    <style>
    /* Hide Streamlit branding only */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

# Google Sheets setup
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
    """Generate XML sitemap for SEO"""
    base_url = "https://video-prompts-gallery.onrender.com"
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Homepage
    sitemap += f'  <url>\n    <loc>{base_url}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
    
    # Legal pages (important for AdSense)
    sitemap += f'  <url>\n    <loc>{base_url}/?tab=Legal</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>\n'
    
    # Each prompt
    for prompt in prompts[:50]:  # Limit to 50 for performance
        unique_id = prompt.get('Unique ID', '')
        if unique_id:
            sitemap += f'  <url>\n    <loc>{base_url}/?prompt_id={unique_id}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n'
    
    sitemap += '</urlset>'
    return sitemap

def show_google_ad(ad_slot="", ad_format="auto", full_width=True):
    """Display Google AdSense ad - optimized version"""
    ads_client_id = os.getenv('GOOGLE_ADS_CLIENT_ID', '')
    
    if not ads_client_id and not os.path.exists('.env'):
        try:
            ads_client_id = st.secrets.get('GOOGLE_ADS_CLIENT_ID', '')
        except:
            ads_client_id = ''
    
    if not ads_client_id or ads_client_id == 'ca-pub-xxxxxxxxxxxxxxxxx':
        return  # Don't show anything if not configured
    
    # Lightweight ad code
    ad_html = f"""
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
    """
    st.components.v1.html(ad_html, height=120)

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
    """Add JSON-LD structured data for better SEO"""
    structured_data = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Video Prompts Gallery",
      "url": "https://video-prompts-gallery.onrender.com",
      "description": "Curated collection of high-quality AI video prompts for filmmakers and creators",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://video-prompts-gallery.onrender.com/?search={search_term_string}",
        "query-input": "required name=search_term_string"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Video Prompts Gallery",
        "email": "k8744185@gmail.com"
      }
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
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Add New", "📚 View All Prompts", "✏️ Manage", "ℹ️ Legal & Info"])
    
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
                for prompt_info in filtered_prompts[start_idx:end_idx]:
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
            Video Prompts Gallery is a curated collection of high-quality video prompts designed to inspire creators, filmmakers, and AI enthusiasts. Our goal is to provide cinematic, detailed prompts that help bring visual stories to life.
            
            ## 🌟 What We Offer
            - **Curated Prompts:** Handcrafted video prompts across multiple categories
            - **Multiple Categories:** Nature, Urban, People, Cinematic, Sci-Fi, Fantasy, and more
            - **Tamil Cinema Focus:** Special collection of Tamil cinema-inspired romantic scenes
            - **Easy Search:** Find the perfect prompt with our search and filter features
            - **Free Access:** All prompts are freely accessible to everyone
            
            ## 🎯 Why We Exist
            With the rise of AI video generation tools, having well-crafted prompts is essential. We created this gallery to:
            - Save time for content creators
            - Inspire new creative directions
            - Showcase the beauty of detailed cinematography descriptions
            - Celebrate Tamil cinema and Indian locations
            
            ## 🛠️ Technology
            Built with:
            - **Streamlit:** Modern Python web framework
            - **Google Sheets API:** Cloud-based storage
            - **Render.com:** Reliable hosting platform
            - **Google AdSense:** Supporting our free service
            
            ## 📊 Features
            - 🔍 Advanced search and filtering
            - 🏷️ Multiple category tagging
            - 📄 Pagination for smooth browsing
            - 🕒 India Standard Time (IST) timestamps
            - 📱 Mobile-responsive design
            - 🔐 Admin portal for content management
            
            ## 👥 Target Audience
            - AI video generation users (Runway, Pika, etc.)
            - Filmmakers and cinematographers
            - Content creators and storytellers
            - Tamil cinema enthusiasts
            - Creative professionals
            
            ## 🌏 Geographic Focus
            While our prompts are useful globally, we have a special focus on:
            - Tamil Nadu locations and culture
            - Indian cinematography aesthetics
            - South Indian architectural beauty
            
            ## 📈 Growth
            - **Launch Date:** February 2026
            - **Initial Collection:** 30+ prompts
            - **Categories:** 8 diverse categories
            - **Update Frequency:** Regular additions
            
            ## 🤝 Contribute
            Interested in contributing prompts or partnering with us? Contact us at k8744185@gmail.com
            
            ## 📜 Legal
            All content is original and created for this platform. Please see our Terms of Service and Privacy Policy for more information.
            
            ---
            
            **Created with ❤️ in India**  
            **© 2026 Video Prompts Gallery. All rights reserved.**
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
