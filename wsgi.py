"""
Minimal Flask app that serves static files and proxies to Streamlit
"""
import os
import subprocess
import time
import sys
import requests
from flask import Flask, send_from_directory, Response, request
from pathlib import Path
import threading

app = Flask(__name__)

# Start Streamlit in background
def start_streamlit():
    time.sleep(2)  # Give Flask time to start first
    subprocess.Popen([
        sys.executable, '-m', 'streamlit', 'run', 'app.py',
        '--server.port=8501',
        '--server.address=127.0.0.1',
        '--server.enableCORS=false',
        '--client.showErrorDetails=false'
    ], env={**os.environ, 'STREAMLIT_SERVER_HEADLESS': 'true'})

# Start Streamlit in a background thread
streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
streamlit_thread.start()

# Serve verification files
@app.route('/google<filename>.html')
def serve_verification(filename):
    """Serve Google verification files"""
    file_path = Path('static') / f'google{filename}.html'
    if file_path.exists():
        return send_from_directory('static', f'google{filename}.html', mimetype='text/html')
    return "Not found", 404

# Proxy everything else to Streamlit
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def proxy_to_streamlit(path):
    """Proxy requests to Streamlit"""
    try:
        # Wait for Streamlit to be ready
        for attempt in range(30):
            try:
                response = requests.get('http://127.0.0.1:8501', timeout=1)
                break
            except:
                if attempt < 29:
                    time.sleep(1)
                else:
                    return "Streamlit not ready", 503
        
        # Proxy the request
        streamlit_url = f'http://127.0.0.1:8501/{path}'
        if request.query_string:
            streamlit_url += f'?{request.query_string.decode()}'
        
        resp = requests.request(
            method=request.method,
            url=streamlit_url,
            data=request.get_data(),
            headers={key: value for key, value in request.headers if key != 'Host'},
            allow_redirects=False,
            timeout=30
        )
        
        return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        return f"Error: {str(e)}", 502

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
