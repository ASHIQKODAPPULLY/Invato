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
import traceback
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add handler to also log to stderr
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
        logger.info("Checking for Google Cloud credentials")
        
        if not creds_json:
            logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
            raise Exception("No Google Cloud credentials found in environment")
            
        logger.info("Found credentials in environment")
        
        try:
            # If it's a JSON string, parse it
            if creds_json.startswith('{'):
                logger.info("Parsing JSON credentials string")
                creds_dict = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
            else:
                logger.info("Loading credentials from file path")
                credentials = service_account.Credentials.from_service_account_file(creds_json)
            
            logger.info("Successfully created credentials object")
            client = vision.ImageAnnotatorClient(credentials=credentials)
            logger.info("Successfully created Vision client")
            return client
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse credentials JSON: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create credentials: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Error in get_vision_client: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    """Apply basic image preprocessing using PIL"""
    try:
        logger.info(f"Starting image preprocessing for: {image_path}")
        
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        # Open image
        logger.info("Opening image with PIL")
        with Image.open(image_path) as img:
            # Log original image details
            logger.info(f"Original image mode: {img.mode}, size: {img.size}")
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                logger.info(f"Converting image from {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Resize if too large
            max_dimension = 2000
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                logger.info(f"Resizing image from {img.size} to {new_size}")
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            logger.info("Converting to grayscale")
            img = img.convert('L')
            
            # Enhance contrast
            logger.info("Enhancing contrast")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Save preprocessed image
            preprocessed_path = image_path + "_processed.jpg"
            logger.info(f"Saving preprocessed image to: {preprocessed_path}")
            img.save(preprocessed_path, 'JPEG', quality=95)
            
            # Verify the saved file
            if not os.path.exists(preprocessed_path):
                logger.error("Failed to save preprocessed image")
                raise Exception("Failed to save preprocessed image")
                
            logger.info("Image preprocessing completed successfully")
            return preprocessed_path
            
    except Exception as e:
        logger.error(f"Error in image preprocessing: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@app.route('/')
def index():
    logger.info("Serving index page")
    return render_template('index.html')

@app.route('/extract-text', methods=['POST'])
def extract_text():
    try:
        logger.info("Received text extraction request")
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        logger.info(f"Received file: {file.filename}")
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'File type not allowed'}), 400
            
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info(f"Saving file to: {filepath}")
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        logger.info("File saved successfully")
        
        try:
            # Preprocess the image
            preprocessed_path = preprocess_image(filepath)
            
            # Initialize Vision client
            client = get_vision_client()

            # Read the preprocessed image
            logger.info("Reading preprocessed image")
            with io.open(preprocessed_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            
            # Perform text detection
            logger.info("Sending request to Google Cloud Vision API")
            response = client.text_detection(image=image)
            
            if response.error.message:
                logger.error(f"Error from Vision API: {response.error.message}")
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))
            
            texts = response.text_annotations
            logger.info(f"Received {len(texts)} text annotations")
            
            if texts:
                text = texts[0].description
                logger.info("Successfully extracted text")
            else:
                text = ""
                logger.info("No text found in image")
            
            # Clean up files
            logger.info("Cleaning up temporary files")
            os.remove(filepath)
            os.remove(preprocessed_path)
            
            return jsonify({
                'success': True,
                'text': text
            })
            
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True) 