from flask import Flask, request, jsonify, render_template
import os
from werkzeug.utils import secure_filename
from PIL import Image
import tempfile
import io
import json
from google.cloud import vision
from google.oauth2 import service_account
import logging
from skimage import io as skio
from skimage.color import rgb2gray
from skimage.filters import threshold_otsu
from skimage.morphology import opening, square
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use temporary directory for uploads
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

def get_vision_client():
    """Get authenticated vision client using credentials from environment"""
    try:
        # Get credentials from environment variable
        creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_json:
            # If it's a JSON string, parse it
            if creds_json.startswith('{'):
                creds_dict = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
            else:
                # If it's a file path
                credentials = service_account.Credentials.from_service_account_file(creds_json)
            
            return vision.ImageAnnotatorClient(credentials=credentials)
        else:
            raise Exception("No Google Cloud credentials found in environment")
    except Exception as e:
        logger.error(f"Error initializing Vision client: {str(e)}")
        raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    """Apply simplified image preprocessing techniques to improve OCR accuracy"""
    # Read image using scikit-image
    img = skio.imread(image_path)
    
    # Resize image if too large (maintain aspect ratio)
    max_dimension = 2000
    height, width = img.shape[:2]
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        new_height = int(height * scale)
        new_width = int(width * scale)
        img = skio.resize(img, (new_height, new_width), anti_aliasing=True)
    
    # Convert to grayscale
    if len(img.shape) > 2:  # If image is color
        gray = rgb2gray(img)
    else:
        gray = img
    
    # Apply thresholding
    thresh = threshold_otsu(gray)
    binary = gray > thresh
    
    # Simple noise removal
    selem = square(2)
    processed = opening(binary, selem)
    
    # Save preprocessed image
    preprocessed_path = image_path + "_processed.jpg"
    skio.imsave(preprocessed_path, (processed * 255).astype(np.uint8))
    
    return preprocessed_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract-text', methods=['POST'])
def extract_text():
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logger.info(f"File saved to {filepath}")
            
            try:
                # Preprocess the image to improve OCR accuracy
                logger.info("Starting image preprocessing")
                preprocessed_path = preprocess_image(filepath)
                logger.info(f"Image preprocessed and saved to {preprocessed_path}")
                
                # Initialize Vision client with credentials
                client = get_vision_client()
                logger.info("Vision client initialized")

                # Read the image file
                with io.open(preprocessed_path, 'rb') as image_file:
                    content = image_file.read()

                image = vision.Image(content=content)
                
                # Perform text detection
                response = client.text_detection(image=image)
                texts = response.text_annotations
                
                if texts:
                    text = texts[0].description
                else:
                    text = ""
                
                logger.info("OCR completed successfully")
                
                # Clean up files
                os.remove(filepath)
                os.remove(preprocessed_path)
                logger.info("Temporary files cleaned up")
                
                if response.error.message:
                    raise Exception(
                        '{}\nFor more info on error messages, check: '
                        'https://cloud.google.com/apis/design/errors'.format(
                            response.error.message))
                
                return jsonify({
                    'success': True,
                    'text': text
                })
                
            except Exception as e:
                logger.error(f"Error during processing: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

# For local development
if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True) 