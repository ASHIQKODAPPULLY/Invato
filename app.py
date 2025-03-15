from flask import Flask, request, jsonify, render_template
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance
import tempfile
import io
import json
from google.cloud import vision
from google.oauth2 import service_account
import logging

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
    """Apply basic image preprocessing using PIL"""
    try:
        # Open image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (maintain aspect ratio)
            max_dimension = 2000
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            img = img.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)  # Increase contrast
            
            # Save preprocessed image
            preprocessed_path = image_path + "_processed.jpg"
            img.save(preprocessed_path, 'JPEG', quality=95)
            
            return preprocessed_path
    except Exception as e:
        logger.error(f"Error in image preprocessing: {str(e)}")
        raise

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
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logger.info(f"File saved to {filepath}")
            
            try:
                # Preprocess the image
                logger.info("Starting image preprocessing")
                preprocessed_path = preprocess_image(filepath)
                logger.info(f"Image preprocessed and saved to {preprocessed_path}")
                
                # Initialize Vision client
                client = get_vision_client()
                logger.info("Vision client initialized")

                # Read the preprocessed image
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

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True) 