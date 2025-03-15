#!/bin/bash

# Add Tesseract repository
apt-get update
apt-get install -y software-properties-common
add-apt-repository -y ppa:alex-p/tesseract-ocr

# Install Tesseract and English language data
apt-get update
apt-get install -y tesseract-ocr
apt-get install -y tesseract-ocr-eng

# Verify installation
tesseract --version 