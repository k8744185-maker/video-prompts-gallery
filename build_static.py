import os
import json
import shutil
import urllib.request
import re

def build_static_project():
    src_dir = "/home/venkadesan.k/Documents/Personalcode"
    dest_dir = "/home/venkadesan.k/Documents/Personalcode1"

    print(f"Building static project from {src_dir} to {dest_dir}...")

    # Create destination directories
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, 'static'), exist_ok=True)
    os.makedirs(os.path.join(dest_dir, 'blog'), exist_ok=True)

    # 1. Fetch live data and save to prompts.json
    print("Fetching live prompt data...")
    latest_data = {"prompts": [], "analytics": [], "comments": []}
    try:
        req = urllib.request.Request("https://video-prompts-gallery.onrender.com/api/v1/prompts")
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                latest_data = json.loads(response.read().decode('utf-8'))
                latest_data['analytics'] = [a for a in latest_data.get('analytics', []) if a.get('Event Type') == 'like']
    except Exception as e:
        print(f"Warning: Could not fetch live data: {e}")

    with open(os.path.join(dest_dir, 'prompts.json'), 'w') as f:
        json.dump(latest_data, f)
    
    # 2. Copy static files
    print("Copying static files...")
    if os.path.exists(os.path.join(dest_dir, 'static')):
        shutil.rmtree(os.path.join(dest_dir, 'static'))
    shutil.copytree(os.path.join(src_dir, 'static'), os.path.join(dest_dir, 'static'))

    # 3. Process and Copy HTML files
    print("Converting HTML files...")
    templates = os.listdir(os.path.join(src_dir, 'templates'))
    for t in templates:
        if not t.endswith('.html'):
            continue
        
        with open(os.path.join(src_dir, 'templates', t), 'r') as f:
            html = f.read()

        # Fix paths for static hosting
        html = html.replace('href="/static/', 'href="./static/')
        html = html.replace('src="/static/', 'src="./static/')
        
        # Determine output path (blog goes into /blog folder)
        if t.startswith('blog_'):
            blog_name = t.replace('blog_', '').replace('.html', '')
            out_path = os.path.join(dest_dir, 'blog', f"{blog_name}.html")
            
            # Additional path fix for nested blog files
            html = html.replace('href="./static/', 'href="../static/')
            html = html.replace('src="./static/', 'src="../static/')
            html = html.replace('href="/blog"', 'href="../blog.html"')
            html = html.replace('href="/"', 'href="../index.html"')
        else:
            if t == 'blog_index.html':
                 out_path = os.path.join(dest_dir, 'blog.html')
            else:
                 out_path = os.path.join(dest_dir, t)
            
            html = html.replace('href="/blog"', 'href="./blog.html"')
            html = html.replace('href="/about"', 'href="./about.html"')
            html = html.replace('href="/contact"', 'href="./contact.html"')
            html = html.replace('href="/"', 'href="./index.html"')

        with open(out_path, 'w') as f:
            f.write(html)

    # 4. Modify app.js for static JSON fetching
    print("Modifying app.js for static architecture...")
    app_js_path = os.path.join(dest_dir, 'static', 'js', 'app.js')
    with open(app_js_path, 'r') as f:
        app_js = f.read()

    js_overrides = """
// --- STATIC SITE OVERRIDES ---
async function fetchData() {
    try {
        const loader = document.getElementById('vpg-loader');
        if (loader) loader.style.display = 'none';

        const response = await fetch('./prompts.json');
        const data = await response.json();
        
        appState.prompts = data.prompts || [];
        appState.analytics = data.analytics || [];
        appState.comments = data.comments || [];

        renderFilters();
        renderGrid();
        handleRouting();
    } catch (e) {
        console.error("Failed to load static prompts data:", e);
    }
}
async function logVisit(id) { return; }
async function checkAuthStatus() { return; }
async function checkAdminSession() { return; }
"""
    app_js += f"\n{js_overrides}\n"
    
    # Hide login features via CSS inject
    css_hide_login = """
\n/* Static Site Mode: Hide all Admin/Login features */
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
    style_css_path = os.path.join(dest_dir, 'static', 'css', 'style.css')
    with open(style_css_path, 'a') as f:
        f.write(css_hide_login)

    # Disable preloader auto-init
    app_js = app_js.replace('initPreloader();', '// initPreloader();')

    with open(app_js_path, 'w') as f:
        f.write(app_js)

    print("✅ Static frontend generated successfully.")

if __name__ == "__main__":
    build_static_project()
