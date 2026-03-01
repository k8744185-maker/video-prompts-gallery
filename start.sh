#!/bin/bash
# Render.com start script with Gunicorn WSGI server

gunicorn --bind 0.0.0.0:$PORT wsgi:application --workers 1 --threads 2 --timeout 30
