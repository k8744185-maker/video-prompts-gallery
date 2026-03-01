"""
WSGI application for Render deployment
"""
import os
import subprocess
import time
import sys
import requests
from flask import Flask, send_from_directory, Response, request
from pathlib import Path

app = Flask(__name__)

# Global variable to track Streamlit process
streamlit_process = None

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

def start_streamlit():
    """Start Streamlit in background"""
    global streamlit_process
    if streamlit_process is None:
        print("Starting Streamlit...")
        streamlit_process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port=8501',
            '--server.address=127.0.0.1',
            '--server.enableCORS=false',
            '--server.headless=true',
            '--client.showErrorDetails=false'
        ], env={**os.environ, 'STREAMLIT_SERVER_HEADLESS': 'true'})
        print("Streamlit started")

# Start Streamlit when module is imported
start_streamlit()

# Give Streamlit time to start
time.sleep(3)

# For Render - export the Flask app
application = app
