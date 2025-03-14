#!/bin/bash
# Install Tesseract
apt-get update
apt-get install -y tesseract-ocr

# Start the application
gunicorn -c gunicorn.conf.py app:app 