"""
Simple Flask app that serves static files and proxies to Streamlit
"""
import os
import subprocess
import time
import sys
import requests
from flask import Flask, send_from_directory, Response, request
from pathlib import Path

app = Flask(__name__)

# Serve verification files
@app.route('/google<filename>.html')
def serve_verification(filename):
    """Serve Google verification files"""
    file_path = Path('static') / f'google{filename}.html'
    if file_path.exists():
        return send_from_directory('static', f'google{filename}.html', mimetype='text/html')
    return "Not found", 404

# Health check
@app.route('/health')
def health():
    return "OK", 200

# Proxy everything else to Streamlit
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def proxy_to_streamlit(path):
    """Proxy requests to Streamlit"""
    try:
        # Streamlit URL
        streamlit_url = f'http://127.0.0.1:8501/{path}'
        if request.query_string:
            streamlit_url += f'?{request.query_string.decode()}'

        # Forward the request
        resp = requests.request(
            method=request.method,
            url=streamlit_url,
            data=request.get_data(),
            headers={key: value for key, value in request.headers if key.lower() not in ['host', 'connection']},
            allow_redirects=False,
            timeout=30
        )

        return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))

    except requests.exceptions.ConnectionError:
        return "Streamlit not available", 503
    except Exception as e:
        return f"Proxy error: {str(e)}", 502

if __name__ == '__main__':
    # Start Streamlit in background
    print("Starting Streamlit...")
    streamlit_process = subprocess.Popen([
        sys.executable, '-m', 'streamlit', 'run', 'app.py',
        '--server.port=8501',
        '--server.address=127.0.0.1',
        '--server.enableCORS=false',
        '--server.headless=true',
        '--client.showErrorDetails=false'
    ], env={**os.environ, 'STREAMLIT_SERVER_HEADLESS': 'true'})

    # Wait a bit for Streamlit to start
    print("Waiting for Streamlit to start...")
    time.sleep(5)

    # Start Flask
    port = int(os.getenv('PORT', 8000))
    print(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
