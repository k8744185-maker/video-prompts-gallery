#!/bin/bash
# Render.com start script - run Streamlit directly

streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=true --server.enableXsrfProtection=false
