#!/bin/bash
# Find Streamlit's index.html and inject Google meta tags + AdSense script into real <head>
STREAMLIT_INDEX=$(python -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static', 'index.html'))")

echo "Patching Streamlit index.html at: $STREAMLIT_INDEX"

# Inject verification + AdSense meta tags + Auto Ads script into real <head>
sed -i 's|<head>|<head><meta name="google-site-verification" content="8MpJT70JgoawSi-Z8yz-ZOHphQiFAsmJTq2622M41Us"/><meta name="google-adsense-account" content="ca-pub-5050768956635718"/><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5050768956635718" crossorigin="anonymous"></script>|' "$STREAMLIT_INDEX"

echo "Patch applied. Starting Streamlit..."

# Run Streamlit directly on Render's PORT
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
