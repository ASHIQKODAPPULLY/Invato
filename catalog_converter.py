import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
import re
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
import subprocess
import sys
import pdfplumber
import fitz  # PyMuPDF

# Set direct paths for dependencies
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Users\ashiq\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

def check_poppler():
    try:
        # Add Poppler to PATH
        os.environ["PATH"] = POPPLER_PATH + os.pathsep + os.environ.get("PATH", "")
        # Try to run poppler's pdfinfo command
        result = subprocess.run([os.path.join(POPPLER_PATH, 'pdfinfo.exe'), '--version'], 
                              capture_output=True, text=True)
        print("Poppler version:", result.stdout.strip())
        return True
    except Exception as e:
        print("Poppler error:", str(e))
        return False

def check_tesseract():
    try:
        # Set Tesseract path
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        # Try to run tesseract command
        result = subprocess.run([TESSERACT_PATH, '--version'], 
                              capture_output=True, text=True)
        print("Tesseract version:", result.stdout.strip())
        return True
    except Exception as e:
        print("Tesseract error:", str(e))
        return False

def configure_poppler():
    print("Checking Poppler installation...")
    print("Current PATH:", os.environ.get("PATH", ""))
    
    if not os.path.exists(POPPLER_PATH):
        print(f"Poppler not found at: {POPPLER_PATH}")
        messagebox.showerror(
            "Poppler Not Found",
            f"Please install Poppler to:\n{POPPLER_PATH}\n\n"
            "Download from: https://github.com/oschwartz10612/poppler-windows/releases/"
        )
        return False
    
    print(f"Found Poppler at: {POPPLER_PATH}")
    os.environ["PATH"] = POPPLER_PATH + os.pathsep + os.environ.get("PATH", "")
    return check_poppler()

def configure_tesseract():
    print("Checking Tesseract installation...")
    
    if not os.path.exists(TESSERACT_PATH):
        print(f"Tesseract not found at: {TESSERACT_PATH}")
        messagebox.showerror(
            "Tesseract Not Found",
            f"Please install Tesseract to:\n{TESSERACT_PATH}\n\n"
            "Download from: https://github.com/UB-Mannheim/tesseract/wiki/Install-Tesseract#windows"
        )
        return False
    
    print(f"Found Tesseract at: {TESSERACT_PATH}")
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    return check_tesseract()

class CatalogConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Saveroo - Catalog Converter")
        self.root.geometry("800x600")
        
        # Check for required dependencies
        if not configure_tesseract() or not configure_poppler():
            root.destroy()
            return
        
        # Set theme colors
        self.primary_color = "#8B5CF6"
        self.secondary_color = "#10B981"
        self.bg_color = "#F3F4F6"
        self.text_color = "#1F2937"
        
        self.root.configure(bg=self.bg_color)
        
        # Main frame
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = tk.Label(
            self.main_frame,
            text="Catalog Converter",
            font=('Arial', 24, 'bold'),
            fg=self.primary_color,
            bg=self.bg_color
        )
        title.pack(pady=20)
        
        # Store selection
        store_frame = ttk.Frame(self.main_frame)
        store_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(store_frame, text="Select Store:").pack(side=tk.LEFT, padx=5)
        self.store_var = tk.StringVar(value="woolworths")
        stores = ["woolworths", "coles", "aldi"]
        store_menu = ttk.OptionMenu(store_frame, self.store_var, "woolworths", *stores)
        store_menu.pack(side=tk.LEFT, padx=5)
        
        # Page selection
        page_frame = ttk.Frame(self.main_frame)
        page_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(page_frame, text="PDF Pages (e.g., 1-5 or 1,3,5):").pack(side=tk.LEFT, padx=5)
        self.page_input = tk.Entry(page_frame)
        self.page_input.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.page_input.insert(0, "1")  # Default to first page for testing
        
        # File selection
        file_frame = ttk.Frame(self.main_frame)
        file_frame.pack(fill=tk.X, pady=10)
        
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        select_button = tk.Button(
            file_frame,
            text="Select PDF",
            command=self.select_file,
            bg=self.primary_color,
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        select_button.pack(side=tk.RIGHT, padx=5)
        
        # Import edited text button
        import_frame = ttk.Frame(self.main_frame)
        import_frame.pack(fill=tk.X, pady=10)
        
        self.import_label = ttk.Label(import_frame, text="No edited text file selected")
        self.import_label.pack(side=tk.LEFT, padx=5)
        
        import_button = tk.Button(
            import_frame,
            text="Import Edited Text",
            command=self.import_edited_text,
            bg=self.primary_color,
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        import_button.pack(side=tk.RIGHT, padx=5)
        
        # Preview frame
        preview_frame = ttk.Frame(self.main_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(preview_frame, text="Extracted Text Preview:").pack(anchor='w')
        
        self.preview_text = tk.Text(preview_frame, height=10, width=60)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Convert button
        self.convert_button = tk.Button(
            self.main_frame,
            text="Convert to CSV",
            command=self.convert_catalog,
            bg=self.secondary_color,
            fg="white",
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        self.convert_button.pack(pady=20)
        
        # Status text
        self.status_text = tk.Text(self.main_frame, height=5, width=60)
        self.status_text.pack(pady=10)
        
        self.selected_file = None
        self.edited_text_file = None

        # Help text
        help_text = """
Instructions:
1. Select the store (Woolworths, Coles, or Aldi)
2. Enter page numbers to convert (e.g., "1-5" or "1,3,5" or "all")
3. Click 'Select PDF' to choose your catalog file
4. Review the preview and edit the generated text file
5. Click 'Import Edited Text' to use your corrected version
6. Click 'Convert to CSV' to create the formatted file

Note: The converter will first extract text from the PDF and save it to a file.
You can then edit this file manually to correct any errors before converting to CSV.
        """
        help_label = tk.Label(
            self.main_frame,
            text=help_text,
            justify=tk.LEFT,
            bg=self.bg_color,
            fg=self.text_color,
            wraplength=700
        )
        help_label.pack(pady=10)

    def select_file(self):
        filetypes = [
            ('PDF files', '*.pdf'),
            ('All files', '*.*')
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.selected_file = filename
            self.file_label.config(text=os.path.basename(filename))
            self.log_message(f"Selected file: {os.path.basename(filename)}")
            self.preview_pdf()

    def log_message(self, message):
        self.status_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')}: {message}\n")
        self.status_text.see(tk.END)

    def extract_text_from_image(self, image):
        try:
            # Save original debug image
            debug_image_path = "debug_page.png"
            image.save(debug_image_path)
            print(f"Saved original image to: {debug_image_path}")
            
            # Convert image to RGB mode if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            from PIL import ImageEnhance, ImageFilter, ImageOps
            import numpy as np
            
            # Split image into regions
            width, height = image.size
            left_margin = width // 6  # Focus on leftmost sixth for prices
            left_region = image.crop((0, 0, left_margin, height))
            center_region = image.crop((width // 3, 0, 2 * width // 3, height))
            
            # First identify yellow regions to exclude them
            r, g, b = left_region.split()
            # Create yellow mask (high red and green, low blue)
            yellow_mask = Image.merge('RGB', (
                ImageEnhance.Contrast(r).enhance(2.5),
                ImageEnhance.Contrast(g).enhance(2.5),
                Image.new('L', r.size, 0)  # Zero out blue
            ))
            yellow_mask = yellow_mask.convert('L')
            # Threshold to isolate yellow regions
            yellow_mask = yellow_mask.point(lambda x: 0 if x > 170 else 255)  # Invert mask to exclude yellow
            
            # Create multiple enhanced versions for different processing techniques
            enhancements = []
            
            # Split left region into smaller vertical sections for better price detection
            left_height = left_region.size[1]
            section_height = left_height // 5  # Process in fifths for more granular detection
            
            for i in range(5):
                start_y = i * section_height
                end_y = (i + 1) * section_height
                
                # Extract section
                section = left_region.crop((0, start_y, left_region.size[0], end_y))
                section_mask = yellow_mask.crop((0, start_y, left_region.size[0], end_y))
                
                # Process section
                enhanced = section.copy()
                # Convert to grayscale
                enhanced = enhanced.convert('L')
                # Apply yellow mask to remove savings text
                enhanced = Image.composite(enhanced, Image.new('L', enhanced.size, 255), section_mask)
                # Increase contrast very significantly
                enhanced = ImageEnhance.Contrast(enhanced).enhance(7.0)
                # Sharpen
                enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=300))
                # Use very aggressive thresholding
                threshold = 120  # Even lower threshold
                enhanced = enhanced.point(lambda x: 255 if x > threshold else 0)
                # Remove noise
                enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))
                enhanced = enhanced.filter(ImageFilter.MinFilter(size=3))
                enhancements.append((f"price_text_{i}", enhanced))
            
            # Enhancement for product name detection (focused on center region)
            enhanced_product = center_region.copy()
            enhanced_product = enhanced_product.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
            enhanced_product = enhanced_product.convert('L')
            enhanced_product = ImageEnhance.Contrast(enhanced_product).enhance(1.8)
            enhanced_product = enhanced_product.filter(ImageFilter.MedianFilter(size=3))
            enhanced_product = ImageOps.autocontrast(enhanced_product, cutoff=2)
            enhancements.append(("product_text", enhanced_product))
            
            # Save all enhanced versions for debugging
            for name, img in enhancements:
                debug_path = f"debug_{name}.png"
                img.save(debug_path)
                print(f"Saved {name} enhanced image to: {debug_path}")
            
            # Try OCR on each enhanced image with different PSM modes
            all_prices = set()
            product_text = ""
            
            for enhancement_name, enhanced_img in enhancements:
                print(f"\nTrying OCR on {enhancement_name} enhancement")
                
                # Resize for better OCR
                width, height = enhanced_img.size
                scale_factor = 4 if "price_text" in enhancement_name else 2  # Even higher scale for prices
                enhanced_img = enhanced_img.resize(
                    (width * scale_factor, height * scale_factor),
                    Image.Resampling.LANCZOS
                )
                
                if "price_text" in enhancement_name:
                    # For price sections, try single line and word modes
                    psm_modes = [7, 8, 13]  # Focus on single line/word modes
                    for psm in psm_modes:
                        try:
                            # Configure for digit and price recognition
                            custom_config = f'--oem 3 --psm {psm} -l eng --dpi 1200 -c tessedit_char_whitelist="0123456789$." textord_heavy_nr=1 tessedit_write_images=1'
                            text = pytesseract.image_to_string(
                                enhanced_img,
                                config=custom_config,
                                timeout=30
                            )
                            
                            # Extract prices with more flexible patterns
                            price_patterns = [
                                r'\$\s*\d+\.?\d*',  # $X.XX or $X
                                r'\d+\.?\d*\s*\$',  # X.XX$ or X$
                                r'\d+\.\d{2}',      # X.XX
                                r'\$?\d{1,3}'       # Basic numbers that might be prices
                            ]
                            
                            for pattern in price_patterns:
                                matches = re.findall(pattern, text)
                                for price in matches:
                                    try:
                                        # Clean up the price string
                                        price_str = re.sub(r'[^\d.]', '', price)
                                        value = float(price_str)
                                        if 0.1 <= value <= 1000:
                                            formatted_price = f"${value:.2f}"
                                            all_prices.add(formatted_price)
                                    except ValueError:
                                        continue
                            
                        except Exception as e:
                            print(f"Error with PSM {psm} on {enhancement_name}: {str(e)}")
                            continue
                else:
                    # For product text, use full page and column modes
                    psm_modes = [3, 4]
                    for psm in psm_modes:
                        try:
                            custom_config = f'--oem 3 --psm {psm} -l eng --dpi 600'
                            text = pytesseract.image_to_string(
                                enhanced_img,
                                config=custom_config,
                                timeout=30
                            )
                            if len(text) > len(product_text):
                                product_text = text
                        except Exception as e:
                            print(f"Error with PSM {psm} on {enhancement_name}: {str(e)}")
                            continue
            
            # Combine results
            combined_text = f"Prices found: {', '.join(sorted(all_prices))}\n\n{product_text}"
            print("\nExtracted Prices:", sorted(all_prices))
            print("\nProduct Text Length:", len(product_text))
            
            return combined_text
            
        except Exception as e:
            print(f"Error in OCR: {str(e)}")
            import traceback
            print("Full error:", traceback.format_exc())
            return ""

    def find_prices(self, text):
        # Look for price patterns: $X.XX, $XX.XX, $XXX.XX
        price_patterns = [
            r'\$\s*\d+\.\d{2}',  # $X.XX
            r'\d+\.\d{2}\s*\$',  # X.XX$
            r'\$\s*\d+',         # $X
            r'\d+\s*\$',         # X$
            r'\$\d+\.\d{2}',     # No space after $
            r'\d+\.\d{2}',       # Just the number
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                price_str = match.group()
                price_str = re.sub(r'[^\d.]', '', price_str)
                try:
                    price = float(price_str)
                    if 0.1 <= price <= 1000:  # Reasonable price range
                        prices.append({
                            'value': price,
                            'start': match.start(),
                            'end': match.end()
                        })
                except ValueError:
                    continue
        return prices

    def extract_product_info(self, text):
        products = []
        prices = self.find_prices(text)
        
        if not prices:
            return []

        # Split text into lines for better context
        lines = text.split('\n')
        current_line_start = 0
        
        for line in lines:
            if not line.strip():
                current_line_start += len(line) + 1
                continue
                
            # Find prices in this line
            line_prices = [p for p in prices if current_line_start <= p['start'] < current_line_start + len(line)]
            
            for price in line_prices:
                # Get context before and after price
                context_start = max(0, current_line_start - 100)
                context_end = min(len(text), current_line_start + len(line) + 100)
                context = text[context_start:context_end]
                
                # Clean up the context
                context = re.sub(r'\s+', ' ', context).strip()
                
                # Remove the price and nearby prices from the context
                context = re.sub(r'\$?\d+\.\d{2}\$?', '', context)
                
                # Try to extract brand (text in parentheses)
                brand = ""
                brand_match = re.search(r'\((.*?)\)', context)
                if brand_match:
                    brand = brand_match.group(1)
                    context = re.sub(r'\s*\(.*?\)\s*', ' ', context)
                
                # Clean up the product name
                name = context.strip()
                name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
                name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
                
                if name:
                    products.append({
                        'name': name,
                        'price': price['value'],
                        'brand': brand
                    })
            
            current_line_start += len(line) + 1
        
        # Remove duplicates while keeping the highest price for each product
        unique_products = {}
        for product in products:
            key = re.sub(r'\s+', '', product['name'].lower())
            if key not in unique_products or unique_products[key]['price'] < product['price']:
                unique_products[key] = product
        
        return list(unique_products.values())

    def extract_text_with_pymupdf(self, pdf_path):
        try:
            print("Attempting PyMuPDF text extraction...")
            doc = fitz.open(pdf_path)
            
            if len(doc) < 2:  # Check if we have at least 2 pages
                print("PDF has less than 2 pages")
                return ""
                
            page = doc[1]  # Get second page
            page_width = page.rect.width
            
            # Get text with detailed information
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            # Lists to store text elements by region
            left_region_text = []    # For prices
            center_region_text = []  # For product names
            right_region_text = []   # For additional info
            
            # Define regions (left third, middle third, right third)
            left_boundary = page_width / 3
            right_boundary = 2 * page_width / 3
            
            for block in blocks:
                if "lines" not in block:
                    continue
                
                block_x = block["bbox"][0]  # x coordinate of block start
                
                for line in block["lines"]:
                    line_text = []
                    line_fonts = []
                    line_sizes = []
                    line_colors = []
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        
                        # Store text with its properties
                        line_text.append(text)
                        line_fonts.append(span["font"])
                        line_sizes.append(span["size"])
                        line_colors.append(span.get("color", 0))
                    
                    if not line_text:
                        continue
                    
                    # Combine line information
                    combined_text = " ".join(line_text)
                    avg_size = sum(line_sizes) / len(line_sizes)
                    
                    # Create text element with properties
                    text_elem = {
                        'text': combined_text,
                        'bbox': line["bbox"],
                        'font_size': avg_size,
                        'fonts': line_fonts,
                        'colors': line_colors,
                        'y_pos': line["bbox"][1]  # y coordinate for sorting
                    }
                    
                    # Categorize text based on position and content
                    if block_x < left_boundary:
                        # Check if text looks like a price
                        if re.search(r'\$?\d+\.?\d*\$?', combined_text):
                            text_elem['is_price'] = True
                            left_region_text.append(text_elem)
                    elif block_x < right_boundary:
                        center_region_text.append(text_elem)
                    else:
                        right_region_text.append(text_elem)
            
            # Sort all regions by vertical position
            left_region_text.sort(key=lambda x: x['y_pos'])
            center_region_text.sort(key=lambda x: x['y_pos'])
            right_region_text.sort(key=lambda x: x['y_pos'])
            
            # Format the output
            output = []
            output.append("=== PYMUPDF TEXT EXTRACTION ===\n")
            
            # Add prices section
            output.append("Detected Prices:")
            output.append("-" * 40)
            for elem in left_region_text:
                if elem.get('is_price', False):
                    output.append(f"Price: {elem['text']} (size: {elem['font_size']:.1f})")
            output.append("")
            
            # Add product text section
            output.append("Detected Products:")
            output.append("-" * 40)
            
            # Try to match prices with product names based on vertical alignment
            y_threshold = 10  # Maximum vertical distance to consider text as related
            
            for center_elem in center_region_text:
                # Find nearby price
                matching_price = None
                for price_elem in left_region_text:
                    if abs(price_elem['y_pos'] - center_elem['y_pos']) <= y_threshold:
                        matching_price = price_elem
                        break
                
                # Format product entry
                if matching_price and matching_price.get('is_price', False):
                    output.append(f"Name: {center_elem['text']}")
                    output.append(f"Price: {matching_price['text']}")
                    
                    # Look for additional info in right region
                    for right_elem in right_region_text:
                        if abs(right_elem['y_pos'] - center_elem['y_pos']) <= y_threshold:
                            output.append(f"Additional Info: {right_elem['text']}")
                            break
                    
                    output.append("-" * 20)
            
            return "\n".join(output)
            
        except Exception as e:
            print(f"PyMuPDF extraction failed: {str(e)}")
            import traceback
            print("Full error:", traceback.format_exc())
            return ""

    def preview_pdf(self):
        try:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "Processing PDF...\n")
            self.root.update()

            print(f"Processing PDF: {self.selected_file}")
            
            # Create output filename based on current time
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_txt = f"catalog_text_{timestamp}.txt"
            
            with open(output_txt, 'w', encoding='utf-8') as f:
                f.write("=== RAW TEXT EXTRACTION ===\n\n")
                
                # Try PyMuPDF extraction first
                pymupdf_text = self.extract_text_with_pymupdf(self.selected_file)
                if pymupdf_text:
                    print("Successfully extracted text using PyMuPDF")
                    f.write(pymupdf_text)
                    f.write("\n\n")
                
                # Then try direct PDF text extraction with pdfplumber
                print("Attempting pdfplumber text extraction...")
                extracted_text = ""
                try:
                    with pdfplumber.open(self.selected_file) as pdf:
                        if len(pdf.pages) > 1:  # Check if we have a second page
                            page = pdf.pages[1]  # Get second page
                            extracted_text = page.extract_text()
                            if extracted_text:
                                print("Successfully extracted text with pdfplumber")
                                print(f"Extracted {len(extracted_text)} characters")
                                f.write("PDFPlumber Extraction:\n")
                                f.write("-" * 40 + "\n")
                                f.write(extracted_text)
                                f.write("\n\n")
                except Exception as e:
                    print(f"PDFPlumber extraction failed: {str(e)}")
                    f.write(f"PDFPlumber extraction failed: {str(e)}\n\n")
                    extracted_text = ""

                # If both direct extractions failed or got no text, try OCR
                if not pymupdf_text.strip() and not extracted_text.strip():
                    print("Direct extractions yielded no text, falling back to OCR...")
                    print(f"Using Poppler from: {POPPLER_PATH}")
                    
                    # Convert second page of PDF to image
                    pages = convert_from_path(
                        self.selected_file,
                        first_page=2,  # Start from second page
                        last_page=2,
                        poppler_path=POPPLER_PATH,
                        dpi=300,
                        use_cropbox=True,
                        strict=False
                    )
                    if not pages:
                        raise Exception("Failed to convert PDF to image")

                    print("Successfully converted PDF page to image")
                    print(f"Image size: {pages[0].size}")
                    print(f"Image mode: {pages[0].mode}")
                    
                    self.preview_text.insert(tk.END, "Extracting text from image...\n")
                    self.root.update()

                    # Extract text from the image
                    f.write("OCR Text Extraction:\n")
                    f.write("-" * 40 + "\n")
                    
                    # Process full page
                    full_text = self.extract_text_from_image(pages[0])
                    f.write("Full Page OCR:\n")
                    f.write(full_text)
                    f.write("\n\n")
                    
                    # Process left region specifically for prices
                    width = pages[0].size[0]
                    left_region = pages[0].crop((0, 0, width // 3, pages[0].size[1]))
                    f.write("Left Region (Prices) OCR:\n")
                    f.write("-" * 40 + "\n")
                    
                    # Try different PSM modes for price detection
                    for psm in [7, 8, 13]:  # Single line and word modes
                        try:
                            config = f'--oem 3 --psm {psm} -l eng --dpi 900 -c tessedit_char_whitelist="0123456789$."'
                            text = pytesseract.image_to_string(left_region, config=config)
                            f.write(f"\nPSM Mode {psm}:\n")
                            f.write(text)
                            f.write("\n")
                        except Exception as e:
                            f.write(f"Error with PSM {psm}: {str(e)}\n")
                    
                    # Process center region for product names
                    center_region = pages[0].crop((width // 3, 0, 2 * width // 3, pages[0].size[1]))
                    f.write("\nCenter Region (Products) OCR:\n")
                    f.write("-" * 40 + "\n")
                    
                    for psm in [3, 4]:  # Full page and column modes
                        try:
                            config = f'--oem 3 --psm {psm} -l eng --dpi 600'
                            text = pytesseract.image_to_string(center_region, config=config)
                            f.write(f"\nPSM Mode {psm}:\n")
                            f.write(text)
                            f.write("\n")
                        except Exception as e:
                            f.write(f"Error with PSM {psm}: {str(e)}\n")
                    
                    extracted_text = full_text

                # Try to find structured information
                f.write("\n=== STRUCTURED INFORMATION ===\n\n")
                
                # Find prices
                prices = self.find_prices(extracted_text)
                f.write("Detected Prices:\n")
                f.write("-" * 40 + "\n")
                for price in prices:
                    f.write(f"${price['value']:.2f}\n")
                
                # Find products
                products = self.extract_product_info(extracted_text)
                f.write("\nDetected Products:\n")
                f.write("-" * 40 + "\n")
                for product in products:
                    f.write(f"Name: {product['name']}\n")
                    f.write(f"Price: ${product['price']:.2f}\n")
                    if product['brand']:
                        f.write(f"Brand: {product['brand']}\n")
                    f.write("-" * 20 + "\n")

            # Update preview text
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Text has been saved to: {output_txt}\n\n")
            self.preview_text.insert(tk.END, "Please edit the file manually to correct any errors.\n")
            self.preview_text.insert(tk.END, "After editing, you can run the conversion again.\n")
            
            print(f"Saved extracted text to: {output_txt}")
            
            # Open the file for the user
            os.startfile(output_txt)

        except Exception as e:
            print(f"Error previewing PDF: {str(e)}")
            import traceback
            print("Full error:", traceback.format_exc())
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Error previewing PDF: {str(e)}")

    def import_edited_text(self):
        filetypes = [
            ('Text files', '*.txt'),
            ('All files', '*.*')
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.edited_text_file = filename
            self.import_label.config(text=os.path.basename(filename))
            self.log_message(f"Selected edited text file: {os.path.basename(filename)}")
            
            # Read and display the edited text
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, "=== Imported Edited Text ===\n\n")
                self.preview_text.insert(tk.END, text)
            except Exception as e:
                self.log_message(f"Error reading edited text: {str(e)}")
                messagebox.showerror("Error", f"Failed to read edited text file: {str(e)}")

    def convert_catalog(self):
        if not self.selected_file and not self.edited_text_file:
            messagebox.showerror("Error", "Please select a PDF file or import edited text file")
            return

        try:
            store = self.store_var.get()
            all_products = []

            if self.edited_text_file:
                # Process the edited text file
                self.log_message("Processing edited text file...")
                with open(self.edited_text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                    
                # Extract structured information section
                structured_section = ""
                if "=== STRUCTURED INFORMATION ===" in text:
                    sections = text.split("=== STRUCTURED INFORMATION ===")
                    structured_section = sections[1]
                else:
                    structured_section = text

                # Parse products section
                products_section = ""
                if "Detected Products:" in structured_section:
                    sections = structured_section.split("Detected Products:")
                    products_section = sections[1]
                else:
                    products_section = structured_section

                # Split into individual product entries
                product_entries = products_section.split("-" * 20)
                
                for entry in product_entries:
                    if not entry.strip():
                        continue
                        
                    # Extract product information
                    name_match = re.search(r'Name:\s*(.+)', entry)
                    price_match = re.search(r'Price:\s*\$?(\d+\.?\d*)', entry)
                    brand_match = re.search(r'Brand:\s*(.+)', entry)
                    
                    if name_match and price_match:
                        product = {
                            'name': name_match.group(1).strip(),
                            'price': float(price_match.group(1)),
                            'brand': brand_match.group(1).strip() if brand_match else "",
                            'store': store
                        }
                        all_products.append(product)
            else:
                # Use original PDF processing
                pages_str = self.page_input.get()
                self.log_message("Converting PDF pages to images...")
                
                if pages_str.lower() == 'all':
                    pages = convert_from_path(self.selected_file)
                else:
                    page_numbers = []
                    for part in pages_str.split(','):
                        if '-' in part:
                            start, end = map(int, part.split('-'))
                            page_numbers.extend(range(start, end + 1))
                        else:
                            page_numbers.append(int(part))
                    pages = convert_from_path(self.selected_file, first_page=min(page_numbers), last_page=max(page_numbers))

                self.log_message(f"Processing {len(pages)} pages...")
                
                for i, page in enumerate(pages):
                    self.log_message(f"Processing page {i+1}...")
                    text = self.extract_text_from_image(page)
                    products = self.extract_product_info(text)
                    all_products.extend(products)

            if not all_products:
                raise ValueError("No valid products found")

            # Remove duplicates
            unique_products = {}
            for product in all_products:
                key = re.sub(r'\s+', '', product['name'].lower())
                if key not in unique_products or unique_products[key]['price'] < product['price']:
                    unique_products[key] = product

            # Save to CSV
            output_filename = f"{store}_catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=['name', 'price', 'brand', 'store'])
                writer.writeheader()
                writer.writerows(unique_products.values())

            self.log_message(f"Successfully converted {len(unique_products)} products")
            self.log_message(f"Saved as: {output_filename}")

            messagebox.showinfo("Success", f"Catalog converted successfully!\nSaved as: {output_filename}")

        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to convert catalog: {str(e)}")

def main():
    try:
        print("Starting Catalog Converter...")
        print("Python version:", sys.version)
        print("Current working directory:", os.getcwd())
        print("Tesseract path:", TESSERACT_PATH)
        print("Poppler path:", POPPLER_PATH)
        
        root = tk.Tk()
        app = CatalogConverter(root)
        
        # Set the initial file if provided
        initial_file = r"C:\Users\ashiq\OneDrive\Desktop\Business\apps\Woolworths - Weekly Specials Catalogue VIC - Offer valid Wed 5 Mar - Tue 11 Mar 2025.pdf"
        if os.path.exists(initial_file):
            app.selected_file = initial_file
            app.file_label.config(text=os.path.basename(initial_file))
            app.preview_pdf()
        
        root.mainloop()
    except Exception as e:
        print("Error starting application:", str(e))
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")

if __name__ == "__main__":
    main() 