from flask import Flask, request, jsonify, render_template
import os
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import cv2
import numpy as np
import tempfile

# Set Tesseract path for Vercel environment
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

app = Flask(__name__)

# Use temporary directory for uploads
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    """Apply simplified image preprocessing techniques to improve OCR accuracy"""
    # Read image using OpenCV
    img = cv2.imread(image_path)
    
    # Resize image if too large (maintain aspect ratio)
    max_dimension = 2000
    height, width = img.shape[:2]
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Simple noise removal
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Save preprocessed image
    preprocessed_path = image_path + "_processed.jpg"
    cv2.imwrite(preprocessed_path, opening)
    
    return preprocessed_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract-text', methods=['POST'])
def extract_text():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Preprocess the image to improve OCR accuracy
            preprocessed_path = preprocess_image(filepath)
            
            # Simplified OCR configuration
            custom_config = r'--oem 3 --psm 6'
            
            # For better language handling
            lang = request.form.get('lang', 'eng')  # Default to English if not specified
            if lang != 'eng':
                custom_config += f' -l {lang}'
                
            # Extract text using Tesseract
            text = pytesseract.image_to_string(Image.open(preprocessed_path), config=custom_config)
            
            # Clean up files
            os.remove(filepath)
            os.remove(preprocessed_path)
            
            return jsonify({
                'success': True,
                'text': text
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    return jsonify({'error': 'File type not allowed'}), 400

# For local development
if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True) 