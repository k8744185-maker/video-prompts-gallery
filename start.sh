#!/bin/bash
echo "Starting Video Prompts Gallery setup..."

# Use Python to patch Streamlit's index.html cleanly
python3 << 'PYEOF'
import os, re

# ── Locate Streamlit's index.html ───────────────────────────────────────────
streamlit_path = __import__('streamlit').__file__
static_dir = os.path.join(os.path.dirname(streamlit_path), 'static')
index_path = os.path.join(static_dir, 'index.html')
print(f"Patching: {index_path}")

with open(index_path, 'r', encoding='utf-8') as f:
    original = f.read()

content = original

# ── GUARD: skip if already patched this run (idempotent) ────────────────────
PATCH_MARKER = '<!-- vpg-patched -->'
if PATCH_MARKER in content:
    print("Already patched — skipping.")
else:
    # ── 1. REPLACE <title> TAG ───────────────────────────────────────────────
    # This is the #1 fix: Google shows <title> text as the search result link.
    # Streamlit defaults to <title>Streamlit</title> — we must replace it.
    content = re.sub(
        r'<title>[^<]*</title>',
        '<title>Video Prompts Gallery - AI Video Prompt Collection</title>',
        content, count=1
    )

    # ── 2. HEAD INJECTION ────────────────────────────────────────────────────
    # Meta tags + JSON-LD + AdSense Auto-Ads script (no manual slot IDs needed)
    # Auto Ads: just the script in <head> is enough — Google places ads automatically.
    head_inject = (
        PATCH_MARKER +
        # Site verification & AdSense account claim
        '<meta name="google-site-verification" content="8MpJT70JgoawSi-Z8yz-ZOHphQiFAsmJTq2622M41Us"/>'
        '<meta name="google-adsense-account" content="ca-pub-5050768956635718"/>'
        # Favicon — Google shows this icon next to the site name in search results
        '<link rel="icon" type="image/svg+xml" href="/static/logo.svg"/>'
        '<link rel="shortcut icon" href="/static/logo.svg"/>'
        '<link rel="apple-touch-icon" href="/static/logo.svg"/>'
        # SEO meta tags
        '<meta name="description" content="Video Prompts Gallery - Free curated collection of professional AI video generation prompts for Runway ML, Pika Labs, and Stable Video Diffusion. Browse 100+ prompts across 8+ categories."/>'
        '<meta name="keywords" content="AI video prompts, video generation, Runway ML prompts, Pika Labs, Stable Video Diffusion, cinematic prompts, text to video"/>'
        '<meta name="robots" content="index, follow"/>'
        '<meta name="author" content="Video Prompts Gallery"/>'
        # Open Graph
        '<meta property="og:site_name" content="Video Prompts Gallery"/>'
        '<meta property="og:title" content="Video Prompts Gallery - AI Video Prompt Collection"/>'
        '<meta property="og:description" content="Free curated collection of professional AI video generation prompts for creators and filmmakers."/>'
        '<meta property="og:type" content="website"/>'
        '<meta property="og:url" content="https://video-prompts-gallery.onrender.com/"/>'
        '<meta property="og:image" content="https://video-prompts-gallery.onrender.com/static/logo.svg"/>'
        # Twitter Card
        '<meta name="twitter:card" content="summary_large_image"/>'
        '<meta name="twitter:title" content="Video Prompts Gallery - AI Video Prompt Collection"/>'
        '<meta name="twitter:description" content="Free AI video generation prompts for Runway ML, Pika Labs, Stable Video Diffusion."/>'
        '<meta name="twitter:image" content="https://video-prompts-gallery.onrender.com/static/logo.svg"/>'
        # JSON-LD 1: WebSite schema
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org",'
        '"@type":"WebSite",'
        '"name":"Video Prompts Gallery",'
        '"alternateName":"Video Prompts Gallery - AI Video Prompt Collection",'
        '"url":"https://video-prompts-gallery.onrender.com/",'
        '"description":"Free curated AI video generation prompts for Runway ML, Pika Labs, and Stable Video Diffusion.",'
        '"dateModified":"2026-03-03",'
        '"potentialAction":{"@type":"SearchAction","target":"https://video-prompts-gallery.onrender.com/?q={search_term_string}","query-input":"required name=search_term_string"}'
        '}</script>'
        # JSON-LD 2: Organization with logo — tells Google which image to show next to site name
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org",'
        '"@type":"Organization",'
        '"name":"Video Prompts Gallery",'
        '"url":"https://video-prompts-gallery.onrender.com/",'
        '"logo":{'
        '"@type":"ImageObject",'
        '"url":"https://video-prompts-gallery.onrender.com/static/logo.svg",'
        '"width":192,'
        '"height":192'
        '},'
        '"sameAs":["https://github.com/k8744185-maker/video-prompts-gallery"],'
        '"contactPoint":{"@type":"ContactPoint","email":"k8744185@gmail.com","contactType":"customer support"}'
        '}</script>'
        # JSON-LD 3: BreadcrumbList — makes Google show "site.com › Page" URL path
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org",'
        '"@type":"BreadcrumbList",'
        '"itemListElement":['
        '{"@type":"ListItem","position":1,"name":"Video Prompts Gallery","item":"https://video-prompts-gallery.onrender.com/"},'
        '{"@type":"ListItem","position":2,"name":"Browse Prompts","item":"https://video-prompts-gallery.onrender.com/#browse"},'
        '{"@type":"ListItem","position":3,"name":"FAQ","item":"https://video-prompts-gallery.onrender.com/#faq"}'
        ']}</script>'
        # JSON-LD 4: WebPage with datePublished/dateModified — makes date appear in snippet
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org",'
        '"@type":"WebPage",'
        '"name":"Video Prompts Gallery - AI Video Prompt Collection",'
        '"url":"https://video-prompts-gallery.onrender.com/",'
        '"description":"Free curated collection of 100+ professional AI video generation prompts across Nature, Urban, Cinematic, Sci-Fi, Fantasy, and Tamil Cinema categories. Optimised for Runway ML, Pika Labs, and Stable Video Diffusion.",'
        '"datePublished":"2024-01-01",'
        '"dateModified":"2026-03-03",'
        '"inLanguage":"en",'
        '"isPartOf":{"@type":"WebSite","name":"Video Prompts Gallery","url":"https://video-prompts-gallery.onrender.com/"},'
        '"publisher":{"@type":"Organization","name":"Video Prompts Gallery","logo":{"@type":"ImageObject","url":"https://video-prompts-gallery.onrender.com/static/logo.svg"}}'
        '}</script>'
        # JSON-LD 5: ItemList of categories — helps Google understand site structure
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org",'
        '"@type":"ItemList",'
        '"name":"AI Video Prompt Categories",'
        '"description":"Browse AI video generation prompts by category",'
        '"url":"https://video-prompts-gallery.onrender.com/",'
        '"itemListElement":['
        '{"@type":"ListItem","position":1,"name":"Nature Prompts","description":"AI video prompts for forests, oceans, and landscapes"},'
        '{"@type":"ListItem","position":2,"name":"Urban Prompts","description":"City life, streets, and architecture prompts"},'
        '{"@type":"ListItem","position":3,"name":"Cinematic Prompts","description":"Film-quality dramatic scene prompts"},'
        '{"@type":"ListItem","position":4,"name":"Sci-Fi Prompts","description":"Futuristic worlds and space exploration prompts"},'
        '{"@type":"ListItem","position":5,"name":"Fantasy Prompts","description":"Magical realms and epic fantasy prompts"},'
        '{"@type":"ListItem","position":6,"name":"Tamil Cinema Prompts","description":"South Indian aesthetic and Tamil cinema style prompts"}'
        ']}</script>'
        # AdSense Auto Ads
        '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5050768956635718" crossorigin="anonymous"></script>'
    )
    content = content.replace('<head>', '<head>' + head_inject, 1)

    # ── 3. BODY INJECTION ────────────────────────────────────────────────────
    # Substantial publisher content visible BEFORE Streamlit JS loads.
    # NEVER fully hidden — only shrinks to a footer once Streamlit is confirmed loaded.
    # This directly satisfies AdSense "publisher content" policy requirement.
    body_inject = (
        '<div id="vpg-pub-content" style="max-width:860px;margin:0 auto;padding:2rem 1.5rem;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#fff;">'

        # Header
        '<div style="text-align:center;padding-bottom:1.5rem;border-bottom:3px solid #667eea;margin-bottom:1.5rem;">'
        '<h1 style="color:#222;margin:0 0 0.4rem;font-size:2rem;">&#127916; Video Prompts Gallery</h1>'
        '<p style="color:#555;margin:0;font-size:1.1rem;">Free AI Video Generation Prompts for Creators &amp; Filmmakers</p>'
        '</div>'

        # About section
        '<div style="padding:1.5rem;margin:1.2rem 0;background:#f8f9fa;border-radius:12px;border-left:4px solid #667eea;">'
        '<h2 style="color:#333;margin-top:0;font-size:1.3rem;">What is Video Prompts Gallery?</h2>'
        '<p style="color:#555;line-height:1.8;margin:0 0 0.8rem;">Video Prompts Gallery is a free, curated collection of professional-grade AI video generation prompts for filmmakers, content creators, and AI enthusiasts. Browse 100+ handcrafted prompts across 8+ categories.</p>'
        '<p style="color:#555;line-height:1.8;margin:0;">Every prompt is crafted with cinematic detail — camera angles, lighting, atmospheric elements, and motion descriptions — optimised for Runway ML, Pika Labs, Stable Video Diffusion, and other text-to-video tools.</p>'
        '</div>'

        # Category grid
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.8rem;margin:1.2rem 0;">'
        '<div style="padding:0.9rem;background:#f0f4ff;border-radius:8px;"><strong>&#127807; Nature</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">Forests, oceans, landscapes</p></div>'
        '<div style="padding:0.9rem;background:#fff4f0;border-radius:8px;"><strong>&#127961; Urban</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">City life, streets, architecture</p></div>'
        '<div style="padding:0.9rem;background:#f0fff4;border-radius:8px;"><strong>&#127916; Cinematic</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">Film-quality drama</p></div>'
        '<div style="padding:0.9rem;background:#f8f0ff;border-radius:8px;"><strong>&#128640; Sci-Fi</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">Futuristic worlds &amp; space</p></div>'
        '<div style="padding:0.9rem;background:#fffff0;border-radius:8px;"><strong>&#9728;&#65039; Fantasy</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">Magical realms &amp; epics</p></div>'
        '<div style="padding:0.9rem;background:#fff0f4;border-radius:8px;"><strong>&#127911; Tamil Cinema</strong><p style="color:#666;font-size:0.85rem;margin:0.2rem 0 0;">South Indian aesthetics</p></div>'
        '</div>'

        # How-to section
        '<div style="padding:1.5rem;background:#fff9f0;border-radius:12px;margin:1.2rem 0;border:1px solid #ffe0b2;">'
        '<h2 style="color:#333;margin-top:0;font-size:1.3rem;">How to Use AI Video Prompts</h2>'
        '<ul style="color:#555;line-height:2.2;padding-left:1.2rem;margin:0;">'
        '<li><strong>Be Specific:</strong> Include colors, textures, and lighting for detailed results</li>'
        '<li><strong>Camera Movement:</strong> Specify dolly shots, pans, tracking, or aerial shots</li>'
        '<li><strong>Mood &amp; Atmosphere:</strong> Use words like serene, dramatic, or ethereal</li>'
        '<li><strong>Art Style References:</strong> Mention noir, golden-hour, or cyberpunk aesthetics</li>'
        '<li><strong>Duration Hint:</strong> Specify short loop or long scene for better AI output</li>'
        '</ul>'
        '</div>'

        # Footer
        '<div style="text-align:center;color:#888;font-size:0.85rem;padding:1rem 0;border-top:1px solid #eee;margin-top:1rem;">'
        '<p style="margin:0 0 0.3rem;">&#169; 2026 Video Prompts Gallery &#8212; Made with &#10084;&#65039; in India</p>'
        '<p style="margin:0;">'
        '<a href="/?tab=Privacy" style="color:#667eea;text-decoration:none;">Privacy Policy</a> &nbsp;|&nbsp;'
        '<a href="/?tab=Terms" style="color:#667eea;text-decoration:none;">Terms</a> &nbsp;|&nbsp;'
        '<a href="/?tab=About" style="color:#667eea;text-decoration:none;">About Us</a> &nbsp;|&nbsp;'
        '<a href="/?tab=Contact" style="color:#667eea;text-decoration:none;">Contact</a>'
        '</p>'
        '</div>'
        '</div>'  # end vpg-pub-content

        # No-JS fallback
        '<noscript>'
        '<div style="max-width:800px;margin:0 auto;padding:2rem;font-family:sans-serif;">'
        '<h1>Video Prompts Gallery - AI Video Prompt Collection</h1>'
        '<p>Video Prompts Gallery is a free, curated collection of professional AI video generation prompts '
        'for filmmakers and content creators. Browse prompts across Nature, Urban, Cinematic, Sci-Fi, '
        'Fantasy, Abstract, and Tamil Cinema categories. Works with Runway ML, Pika Labs, and Stable Video Diffusion.</p>'
        '</div>'
        '</noscript>'

        # JS: NEVER fully hide publisher-content.
        # Confirms Streamlit is TRULY loaded (actual prompt text visible, not just spinner),
        # then shrinks to a minimal sticky footer.
        '<script>'
        '(function(){'
        '  var el = document.getElementById("vpg-pub-content");'
        '  if (!el) return;'
        '  var done = false;'
        '  function toFooter(){'
        '    if(done) return; done=true;'
        '    el.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:9999;margin:0;padding:0;";'
        '    el.innerHTML = '
        '      "<div style=\\"background:#f8f9fa;border-top:1px solid #ddd;padding:5px 1rem;'
        'text-align:center;font-size:0.78rem;color:#888;\\">'
        '&#169; 2026 <a href=\\"/\\" style=\\"color:#667eea;font-weight:600;text-decoration:none;\\">'
        'Video Prompts Gallery</a>'
        ' &mdash; Free AI Video Prompts &nbsp;|&nbsp;'
        '<a href=\\"/?tab=Privacy\\" style=\\"color:#888;text-decoration:none;\\">Privacy</a>'
        ' &nbsp;|&nbsp;'
        '<a href=\\"/?tab=About\\" style=\\"color:#888;text-decoration:none;\\">About</a>'
        '</div>";'
        '  }'
        # Wait for real Streamlit content: stMarkdown paragraphs indicate full render
        '  var obs = new MutationObserver(function(){'
        '    var real = document.querySelectorAll(".stMarkdown p");'
        '    if(real.length >= 5){ toFooter(); obs.disconnect(); }'
        '  });'
        '  obs.observe(document.body,{childList:true,subtree:true});'
        # Absolute fallback: 90 seconds (covers Render cold-start delay)
        '  setTimeout(toFooter, 90000);'
        '})();'
        '</script>'
    )
    content = content.replace('<body>', '<body>' + body_inject, 1)

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("index.html patched successfully!")

PYEOF

# Copy static files to Streamlit's static directory
STREAMLIT_STATIC=$(python -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static'))")
cp static/ads.txt "$STREAMLIT_STATIC/ads.txt"
cp static/google7b16d249e9588da5.html "$STREAMLIT_STATIC/google7b16d249e9588da5.html" 2>/dev/null || true
cp static/logo.svg "$STREAMLIT_STATIC/logo.svg" 2>/dev/null || true
cp static/sitemap.xml "$STREAMLIT_STATIC/sitemap.xml" 2>/dev/null || true
cp robots.txt "$STREAMLIT_STATIC/robots.txt" 2>/dev/null || true

echo "All patches applied. Starting Streamlit..."
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
