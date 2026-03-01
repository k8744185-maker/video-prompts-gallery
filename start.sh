#!/bin/bash
# Find Streamlit's static folder
STREAMLIT_STATIC=$(python -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static'))")
STREAMLIT_INDEX="$STREAMLIT_STATIC/index.html"

echo "Patching Streamlit at: $STREAMLIT_STATIC"

# 1. Inject verification + AdSense meta tags + Auto Ads script into real <head>
sed -i 's|<head>|<head><meta name="google-site-verification" content="8MpJT70JgoawSi-Z8yz-ZOHphQiFAsmJTq2622M41Us"/><meta name="google-adsense-account" content="ca-pub-5050768956635718"/><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5050768956635718" crossorigin="anonymous"></script>|' "$STREAMLIT_INDEX"

# 2. Copy ads.txt to Streamlit's root static folder so it's served at /ads.txt
cp static/ads.txt "$STREAMLIT_STATIC/ads.txt"

echo "Patches applied. Starting Streamlit..."

# Run Streamlit directly on Render's PORT
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
