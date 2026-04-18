
import os
import re
import json
import urllib.request

# Paths
BASE_DIR = os.getcwd()
INDEX_HTML = os.path.join(BASE_DIR, 'templates', 'index.html')
STYLE_CSS = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
APP_JS = os.path.join(BASE_DIR, 'static', 'js', 'app.js')
OUTPUT_FILE = os.path.join(BASE_DIR, 'dist', 'sites_google_embed.html')
LIVE_URL = "https://video-prompts-gallery.onrender.com"

def main():
    print("Bundling project for Google Sites (Independent Standalone Version)...")
    
    if not os.path.exists(INDEX_HTML):
        print(f"Error: {INDEX_HTML} not found.")
        return
        
    with open(INDEX_HTML, 'r', encoding='utf-8') as f:
        html = f.read()
    with open(STYLE_CSS, 'r', encoding='utf-8') as f:
        css = f.read()
    with open(APP_JS, 'r', encoding='utf-8') as f:
        js = f.read()

    # --- LIVE DATA FETCHING ---
    latest_data = {"prompts": [], "analytics": [], "comments": []}
    try:
        with urllib.request.urlopen(f"{LIVE_URL}/api/v1/prompts") as response:
            if response.status == 200:
                latest_data = json.loads(response.read().decode())
                latest_data['analytics'] = [a for a in latest_data.get('analytics', []) if a.get('Event Type') == 'like']
                print(f"✅ Fetched {len(latest_data.get('prompts', []))} prompts.")
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch live data: {e}")

    # Remove Preloader HTML (Simple string remove)
    html = html.replace('<!-- Cinematic Preloader -->', '')
    html = html.replace('<div id="vpg-loader">', '<div id="vpg-loader" style="display:none">')

    # --- GOOGLE SITES INDEPENDENCE: CSS HIDE ---
    # Hide all Admin/Login/Auth elements permanently via CSS
    css_hide_login = """
    /* Standalone Google Sites Mode: Hide all Admin/Login features */
    .vpg-nav-link[onclick*="openAuthModal"], 
    .vpg-nav-link[onclick*="userLogout"],
    .footer-link-btn[onclick*="openAdminLogin"],
    .footer-link-btn[onclick*="openAuthModal"],
    #vpg-user-badge, #vpg-admin-bar, 
    #vpg-admin-login-modal, #vpg-auth-modal, #vpg-prompt-editor,
    [ondblclick*="openAdminLogin"] { 
        display: none !important; 
    }
    """
    
    # Inline CSS
    css_tag = f"<style>\n{css}\n{css_hide_login}\n</style>"
    html = html.replace('<link rel="stylesheet" href="/static/css/style.css?v=2">', css_tag)
    html = html.replace('<link rel="stylesheet" href="/static/css/style.css">', css_tag)

    # Modify JS to handle static data ONLY
    js_inject_logic = """
// --- STANDALONE GOOGLE SITES OVERRIDES ---
async function fetchData() {
    const loader = document.getElementById('vpg-loader');
    if (loader) loader.style.display = 'none';

    if (window.STATIC_PROMPTS_DATA) {
        appState.prompts = window.STATIC_PROMPTS_DATA.prompts || [];
        appState.analytics = window.STATIC_PROMPTS_DATA.analytics || [];
        appState.comments = window.STATIC_PROMPTS_DATA.comments || [];
        renderFilters(); renderGrid(); handleRouting();
    }
}
async function logVisit(id) { return; }
async function checkAuthStatus() { return; }
async function checkAdminSession() { return; }
    """
    js += f"\n{js_inject_logic}\n"

    # Disable initPreloader 
    js = js.replace('initPreloader();', '// initPreloader();')

    # Inline JS
    js_tag = f"<script>\n{js}\n</script>"
    html = html.replace('<script src="/static/js/app.js?v=2.0"></script>', js_tag)
    html = html.replace('<script src="/static/js/app.js"></script>', js_tag)
    
    # Data Injection
    json_data = json.dumps(latest_data, separators=(',', ':'))
    injection = f"<script>window.STATIC_PROMPTS_DATA = {json_data}; window.SHARE_BASE_URL = '';</script>"
    html = html.replace('</head>', f"{injection}\n</head>")
    
    # Fix relative URLs
    html = html.replace('href="/static/', f'href="{LIVE_URL}/static/')
    html = html.replace('src="/static/', f'src="{LIVE_URL}/static/')
    html = html.replace('href="/blog"', f'href="{LIVE_URL}/blog"')
    html = html.replace('href="/about"', f'href="{LIVE_URL}/about"')
    html = html.replace('href="/contact"', f'href="{LIVE_URL}/contact"')
    html = html.replace('href="/"', f'href="{LIVE_URL}/"')
    
    # Save the result
    if not os.path.exists(os.path.dirname(OUTPUT_FILE)):
        os.makedirs(os.path.dirname(OUTPUT_FILE))
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"🚀 Successfully created Standalone Bundle for Google Sites: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
