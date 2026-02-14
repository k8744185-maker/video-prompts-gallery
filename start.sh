#!/bin/bash
# Render.com start script
streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=true
