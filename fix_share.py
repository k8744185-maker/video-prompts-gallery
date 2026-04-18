import os
import re

file_path = "/home/venkadesan.k/Documents/Personalcode1/static/js/app.js"
with open(file_path, "r") as f:
    js = f.read()

# Completely replace the sharePrompt function in Personalcode1 to NEVER link to Onrender, 
# and handle the googleusercontent sandbox issue safely.
replacement = """function sharePrompt(id) {
    let base = window.SHARE_BASE_URL || '';
    
    // If inside Google Sites Sandboxed iframe, location.origin is ugly .googleusercontent.com
    if (location.hostname.includes('googleusercontent.com') || location.origin === 'null') {
        // Fallback to a placeholder if they haven't set SHARE_BASE_URL
        base = base || 'https://sites.google.com/view/YOUR-SITE-NAME'; 
        showToast('⚠️ Using placeholder link. Please set SHARE_BASE_URL in index.html');
    } else {
        base = base || (location.origin + location.pathname);
    }
    
    const url = `${base.replace(/\\/$/, '')}/?prompt_id=${encodeURIComponent(id)}`;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            showToast('🔗 Share link copied: ' + url);
        }).catch(() => fallbackCopy(url, () => showToast('🔗 Link copied!')));
    } else {
        fallbackCopy(url, () => showToast('🔗 Link copied!'));
    }
}"""

js = re.sub(r'function sharePrompt\(id\) \{.*?(?=function showToast)', replacement + '\n\n', js, flags=re.DOTALL)

with open(file_path, "w") as f:
    f.write(js)

print("Fixed app.js in Personalcode1")
