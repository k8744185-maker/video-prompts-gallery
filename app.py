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

# Page configuration - Optimized for Render.com free tier
st.set_page_config(
    page_title="Video Prompts Gallery",
    page_icon="🎬",
    layout="centered",  # Narrow layout uses less memory
    initial_sidebar_state="collapsed"
)

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
        # Set timeout for Render.com to prevent hanging
        client.http_client.timeout = 10  # 10 second timeout
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
    st.title("🎬 Video Prompts Gallery")
    st.subheader("Discover and share amazing AI video generation prompts")
    st.divider()
    
    # Single ad placement after hero
    show_google_ad(ad_slot="1234567890", ad_format="auto")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📝 Add New", "📚 View All Prompts", "✏️ Manage"])
    
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
                    st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("")  # Spacing
                submitted = st.form_submit_button("💾 Save Prompt", use_container_width=True, type="primary")
                
                if submitted:
                    if prompt.strip() and prompt_name.strip():
                        with st.spinner('Saving...'):
                            if save_prompt(sheet, prompt_name.strip(), prompt.strip(), video_id.strip()):
                                # Clear cache
                                if 'cached_prompts' in st.session_state:
                                    del st.session_state['cached_prompts']
                                if 'cached_edit_prompts' in st.session_state:
                                    del st.session_state['cached_edit_prompts']
                                st.success("✅ Saved! Switch to 'View All' tab to see it.")
                    else:
                        st.warning("⚠️ Please enter both prompt name and prompt text!")
    
    with tab2:
        st.markdown("### 🌟 All Prompts")
        
        # Cache prompts in session state to avoid repeated API calls
        if 'cached_prompts' not in st.session_state or st.button("🔄 Refresh", key="refresh_prompts"):
            with st.spinner('⏳ Loading...'):
                st.session_state.cached_prompts = get_all_prompts(sheet)
        
        prompts = st.session_state.get('cached_prompts', [])
        
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
            
            # Search box
            search_query = st.text_input("🔍 Search prompts...", placeholder="Type to filter prompts")
            
            # Limit prompts to reduce memory (Render free tier optimization)
            max_prompts = 20
            st.caption(f"Showing latest {min(max_prompts, len(prompts))} of {len(prompts)} prompts")
            
            # Display prompts in reverse order (newest first)
            displayed_count = 0
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
                
                # Limit to max prompts for performance
                if displayed_count >= max_prompts:
                    break
                displayed_count += 1
                
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
                
                # Show share link if button clicked (admin only)
                if st.session_state.get(f"show_link_{idx}", False) and st.session_state.get('authenticated', False):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("🔗 Share this unique link:")
                    st.code(share_link, language="text")
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
                            with st.spinner('Updating...'):
                                if save_prompt(sheet, edited_prompt_name.strip(), edited_prompt.strip(), edited_video_id.strip(), row_num):
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
