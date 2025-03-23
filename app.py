from flask import Flask, request, jsonify, render_template, send_from_directory
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, UnidentifiedImageError
import tempfile
import io
import json
from google.cloud import vision
from google.oauth2 import service_account
import logging
import traceback
import sys
from pdf2image import convert_from_path
import shutil
from dotenv import load_dotenv
import mimetypes

# Load environment variables from .env file
load_dotenv()

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

# Print environment variables for debugging
logger.info("Environment variables:")
logger.info(f"FLASK_APP: {os.getenv('FLASK_APP')}")
logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
logger.info(f"FLASK_DEBUG: {os.getenv('FLASK_DEBUG')}")
logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

app = Flask(__name__, static_folder='static')

# Use temporary directory for uploads
app.config['UPLOAD_FOLDER'] = '/tmp' if os.path.exists('/tmp') else tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'pdf'}
ALLOWED_MIMETYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 
    'image/tiff', 'image/webp', 'application/pdf'
}

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

def get_vision_client():
    """Get authenticated vision client using credentials"""
    try:
        # Check for credentials in environment variable
        creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            try:
                # Parse credentials from JSON string
                creds_dict = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                logger.info("Successfully created credentials from JSON string")
            except Exception as e:
                logger.error(f"Failed to parse credentials JSON: {str(e)}")
                raise
        else:
            # Fall back to credentials file
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path:
                raise Exception("No Google Cloud credentials found")
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            logger.info("Successfully created credentials from file")

        # Create and return the client
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logger.info("Successfully created Vision client")
        return client

    except Exception as e:
        logger.error(f"Error in get_vision_client: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def allowed_file(filename, mimetype=None):
    """Check if file is allowed based on extension and mimetype"""
    extension_ok = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    mimetype_ok = mimetype in ALLOWED_MIMETYPES if mimetype else True
    return extension_ok and mimetype_ok

def preprocess_image(image_path):
    """Apply basic image preprocessing using PIL"""
    try:
        logger.info(f"Starting image preprocessing for: {image_path}")
        
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        # Open image and log details
        logger.info("Opening image with PIL")
        try:
            with Image.open(image_path) as img:
                # Log detailed image information
                logger.info(f"Original image details:")
                logger.info(f"- Mode: {img.mode}")
                logger.info(f"- Size: {img.size}")
                logger.info(f"- Format: {img.format}")
                
                try:
                    # Convert to RGB if needed
                    if img.mode not in ['RGB', 'L']:
                        logger.info(f"Converting image from {img.mode} to RGB")
                        img = img.convert('RGB')
                    
                    # Resize if too large
                    max_dimension = 4000  # Increased from 2000
                    if max(img.size) > max_dimension:
                        ratio = max_dimension / max(img.size)
                        new_size = tuple(int(dim * ratio) for dim in img.size)
                        logger.info(f"Resizing image from {img.size} to {new_size}")
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Convert to grayscale
                    if img.mode != 'L':
                        logger.info("Converting to grayscale")
                        img = img.convert('L')
                    
                    # Enhance contrast
                    logger.info("Enhancing contrast")
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.5)  # Reduced from 2.0 for better screenshot handling
                    
                    # Save preprocessed image with high quality
                    preprocessed_path = image_path + "_processed.jpg"
                    logger.info(f"Saving preprocessed image to: {preprocessed_path}")
                    img.save(preprocessed_path, 'JPEG', quality=95, optimize=True)
                    
                    # Verify the saved file
                    if not os.path.exists(preprocessed_path):
                        logger.error("Failed to save preprocessed image")
                        raise Exception("Failed to save preprocessed image")
                    
                    # Log preprocessed image details
                    with Image.open(preprocessed_path) as processed_img:
                        logger.info(f"Preprocessed image details:")
                        logger.info(f"- Mode: {processed_img.mode}")
                        logger.info(f"- Size: {processed_img.size}")
                        logger.info(f"- Format: {processed_img.format}")
                    
                    logger.info("Image preprocessing completed successfully")
                    return preprocessed_path
                    
                except Exception as e:
                    logger.error(f"Error during image conversion/processing: {str(e)}")
                    raise
        except UnidentifiedImageError:
            logger.error("Could not identify image file format")
            raise Exception("Could not identify image file format. Please ensure it's a valid image file.")
            
    except Exception as e:
        logger.error(f"Error in image preprocessing: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def process_pdf(pdf_path):
    """Convert PDF to images and extract text from each page"""
    try:
        logger.info(f"Processing PDF file: {pdf_path}")
        
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        if not images:
            logger.error("No pages found in PDF")
            raise Exception("No pages found in PDF")
            
        logger.info(f"Converted PDF to {len(images)} pages")
        
        all_text = []
        client = get_vision_client()
        
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1}")
            
            # Save image temporarily
            temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'page_{i}.jpg')
            image.save(temp_image_path, 'JPEG')
            
            # Preprocess the image
            preprocessed_path = preprocess_image(temp_image_path)
            
            # Extract text from the preprocessed image
            with io.open(preprocessed_path, 'rb') as image_file:
                content = image_file.read()
                
            vision_image = vision.Image(content=content)
            response = client.text_detection(image=vision_image)
            
            if response.error.message:
                logger.error(f"Error from Vision API: {response.error.message}")
                raise Exception(response.error.message)
            
            texts = response.text_annotations
            if texts:
                all_text.append(texts[0].description)
            
            # Clean up temporary files
            os.remove(temp_image_path)
            os.remove(preprocessed_path)
        
        return '\n\n--- Page Break ---\n\n'.join(all_text)
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@app.route('/')
def index():
    logger.info("Serving index page")
    return render_template('index.html')

@app.route('/extract-text', methods=['POST'])
def extract_text():
    temp_files = []
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file was uploaded. Please select a file.'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file was selected. Please choose a file.'}), 400
        
        if not allowed_file(file.filename, file.content_type):
            return jsonify({
                'error': 'Invalid file type. Please upload an image (PNG, JPG, etc.) or PDF file.'
            }), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        temp_files.append(temp_path)

        try:
            client = get_vision_client()
            
            if filename.lower().endswith('.pdf'):
                extracted_text = process_pdf(temp_path)
            else:
                preprocessed_path = preprocess_image(temp_path)
                temp_files.append(preprocessed_path)
                
                with io.open(preprocessed_path, 'rb') as image_file:
                    content = image_file.read()
                    
                vision_image = vision.Image(content=content)
                response = client.text_detection(image=vision_image)
                
                if response.error.message:
                    raise Exception(f"Error processing image: {response.error.message}")
                
                texts = response.text_annotations
                if not texts:
                    return jsonify({
                        'success': True,
                        'text': '',
                        'message': 'No text was found in the image.'
                    })
                
                extracted_text = texts[0].description
            
            return jsonify({
                'success': True,
                'text': extracted_text
            })
            
        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'An unexpected error occurred. Please try again.'
        }), 500
        
    finally:
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error cleaning up temp file {temp_file}: {str(e)}")

# Vercel requires a module-level 'app' variable
application = app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 