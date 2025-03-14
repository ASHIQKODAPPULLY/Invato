# Invato - Smart Document Processing

Invato is a modern web application that uses advanced OCR (Optical Character Recognition) technology to extract text from images and PDF documents. Built with Flask and Tesseract OCR, it provides a user-friendly interface for document processing.

![Invato Screenshot](screenshot.png)

## Features

- 📱 Responsive design that works on all devices
- 📷 Direct camera capture support on mobile devices
- 📄 Support for multiple file formats (PNG, JPG, PDF)
- 🔍 Advanced OCR with high accuracy
- 📋 Easy copy-to-clipboard functionality
- 🌐 Modern, intuitive web interface
- 📱 Mobile-first design with touch optimization
- 🔒 Secure file processing

## Tech Stack

- Python 3.8+
- Flask
- Tesseract OCR
- OpenCV
- PyMuPDF
- HTML5/CSS3/JavaScript

## Prerequisites

Before running the application, make sure you have:

1. Python 3.8 or higher installed
2. Tesseract OCR installed on your system:
   - Windows: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`
3. Git installed on your system

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/invato.git
cd invato
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Update Tesseract path in `app.py` (Windows only):
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Upload an image or PDF file by either:
   - Dragging and dropping onto the upload area
   - Clicking/tapping to select a file
   - Using the camera on mobile devices

4. Wait for the text extraction process to complete
5. View the extracted text and use the copy button to copy it to your clipboard

## Development

To contribute to the project:

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text recognition
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [OpenCV](https://opencv.org/) for image processing
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for PDF handling 