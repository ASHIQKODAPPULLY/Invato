import cv2
import pytesseract
import re
import csv
from PIL import Image
import requests
from io import BytesIO
import numpy as np
from datetime import datetime
import os

class CatalogScraper:
    def __init__(self):
        """Initialize the catalog scraper with default settings"""
        # Configure Tesseract path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        self.price_patterns = [
            r"\$\s*(\d+\.?\d{0,2})",  # Standard price format ($XX.XX)
            r"(\d+\.?\d{0,2})\s*\$",  # Price with $ at end
            r"(\d+\.?\d{0,2})\s*ea",  # Price with 'ea' suffix
            r"(\d+\.?\d{0,2})\s*each", # Price with 'each' suffix
            r"(\d+\.?\d{0,2})",  # Just numbers that look like prices
            r"(\d+)",  # Any number
        ]
        
    def enhance_image(self, image):
        """Apply various image processing techniques to improve OCR accuracy"""
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(gray)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(contrast, (3,3), 0)
        
        # Apply Otsu's thresholding
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to clean up text
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Save debug images
        cv2.imwrite('debug_contrast.png', contrast)
        cv2.imwrite('debug_binary.png', binary)
        cv2.imwrite('debug_cleaned.png', cleaned)
        
        return cleaned
        
    def extract_text_regions(self, image, is_product=False):
        """Extract text regions from the image"""
        # Find contours
        contours, _ = cv2.findContours(
            image, cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Get bounding boxes for text regions
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Different size requirements for prices vs products
            if is_product:
                if w > 50 and h > 20:  # Larger regions for products
                    regions.append((x, y, w, h))
            else:
                if w > 5 and h > 5:  # Small regions for prices
                    regions.append((x, y, w, h))
                
        # Draw regions on debug image
        debug_img = cv2.cvtColor(image.copy(), cv2.COLOR_GRAY2BGR)
        for x, y, w, h in regions:
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite('debug_regions.png', debug_img)
                
        return regions
        
    def extract_text_from_region(self, image, region, is_product=False):
        """Extract text from a specific region using OCR"""
        x, y, w, h = region
        roi = image[y:y+h, x:x+w]
        
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Scale up the region for better OCR (use smaller scale)
        scale = 2 if is_product else 1.5
        roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Apply adaptive thresholding
        roi = cv2.adaptiveThreshold(
            roi, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # Convert to PIL Image for Tesseract
        roi_pil = Image.fromarray(roi)
        
        # Try different PSM modes based on type
        if is_product:
            psm_modes = [6, 3]  # Uniform block, auto
            custom_config = '--oem 3 --psm {}'
        else:
            psm_modes = [7, 8, 6]  # Single line, single word, uniform block
            custom_config = '--oem 3 --psm {}'
        
        results = []
        for psm in psm_modes:
            text = pytesseract.image_to_string(
                roi_pil,
                config=custom_config.format(psm),
                lang='eng'
            ).strip()
            
            if text:
                # Clean up the text
                text = ' '.join(text.split())  # Remove extra whitespace
                text = re.sub(r'[^\w\s$.-]', '', text)  # Remove special characters
                
                # Additional cleaning for product text
                if is_product:
                    # Extract product name and price if present
                    price_match = re.search(r'\$(\d+\.?\d{0,2})\s*(?:per\s*kg)?', text)
                    if price_match:
                        price = price_match.group(0)
                        text = text.replace(price, '').strip()
                    
                    # Remove common noise words
                    noise_words = ['SAVE', 'BUY', 'FROM', 'THE', 'FREEZER', 'ONLY', 'AT']
                    for word in noise_words:
                        text = re.sub(r'\b' + word + r'\b', '', text, flags=re.IGNORECASE)
                    
                    # Clean up remaining text
                    text = ' '.join(text.split())  # Remove extra whitespace again
                    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
                    text = text.strip()
                
                if text:  # Only add non-empty text
                    results.append(text)
        
        # Save region for debugging with compression
        cv2.imwrite(f'debug_region_{x}_{y}.jpg', roi, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        # Clean up memory
        del roi
        del roi_pil
        import gc
        gc.collect()
        
        # Return the longest result (usually the most complete)
        return max(results, key=len, default='') if results else ''
        
    def extract_price(self, text):
        """Extract price from text using multiple patterns"""
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Convert to float and format to 2 decimal places
                    price = float(matches[0])
                    # Filter out unreasonable prices (allow anything that looks like a price)
                    if 0.01 <= price <= 1000:
                        return f"{price:.2f}"
                except ValueError:
                    continue
        return None
        
    def extract_product_name(self, text, price_text):
        """Extract product name from text by removing price and cleaning"""
        # Remove price from text
        product_text = text.replace(price_text, '').strip()
        
        # Clean up the product name
        product_text = re.sub(r'\s+', ' ', product_text)  # Remove extra spaces
        product_text = re.sub(r'[^\w\s-]', '', product_text)  # Remove special chars
        
        return product_text.strip()
        
    def process_catalog_image(self, image_path, output_csv, store_name="Unknown", is_url=False):
        """Process a catalog image and extract product information"""
        try:
            # Load image
            if is_url:
                response = requests.get(image_path)
                image = Image.open(BytesIO(response.content))
                image = np.array(image)
            else:
                image = cv2.imread(image_path)
                
            if image is None:
                raise ValueError("Failed to load image")
                
            # Save original image for debugging
            cv2.imwrite('debug_original.png', image)
            
            # Enhance image
            processed_image = self.enhance_image(image)
            
            # Extract text regions
            regions = self.extract_text_regions(processed_image)
            
            products = []
            for region in regions:
                text = self.extract_text_from_region(processed_image, region)
                
                # Look for price in the text
                for pattern in self.price_patterns:
                    price_match = re.search(pattern, text)
                    if price_match:
                        price_text = price_match.group(0)
                        price = self.extract_price(price_text)
                        if price:
                            product_name = self.extract_product_name(text, price_text)
                            if len(product_name) > 3:  # Filter out very short names
                                products.append([product_name, price, store_name])
                                break
            
            # Write results to CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if not output_csv:
                output_csv = f"catalog_products_{timestamp}.csv"
                
            with open(output_csv, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Product", "Price", "Store"])
                writer.writerows(products)
                
            print(f"Extracted {len(products)} products from catalog image")
            return len(products)
            
        except Exception as e:
            print(f"Error processing catalog image: {str(e)}")
            return 0
            
    def process_multiple_images(self, image_paths, output_csv, store_name="Unknown"):
        """Process multiple catalog images and combine results"""
        all_products = []
        
        for image_path in image_paths:
            try:
                # Process each image
                if isinstance(image_path, str):
                    is_url = image_path.startswith(('http://', 'https://'))
                else:
                    is_url = False
                    
                # Create temporary CSV for this image
                temp_csv = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                products_found = self.process_catalog_image(
                    image_path, temp_csv, store_name, is_url
                )
                
                # Read products from temporary CSV
                if products_found > 0:
                    with open(temp_csv, 'r', newline='', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        next(reader)  # Skip header
                        all_products.extend(list(reader))
                        
                # Clean up temporary file
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
                    
            except Exception as e:
                print(f"Error processing image {image_path}: {str(e)}")
                continue
                
        # Write combined results
        if all_products:
            with open(output_csv, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Product", "Price", "Store"])
                writer.writerows(all_products)
                
        return len(all_products)

def main():
    # Example usage
    scraper = CatalogScraper()
    
    # Process the catalog PDF
    pdf_path = "Woolworths - Weekly Specials Catalogue VIC - Offer valid Wed 5 Mar - Tue 11 Mar 2025.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: Could not find PDF file: {pdf_path}")
        return
        
    print(f"Processing catalog: {pdf_path}")
    
    # Check for existing progress
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = None
    problematic_path = None
    last_page = 0
    products = []
    problematic = []
    
    # Look for most recent CSV file
    csv_files = [f for f in os.listdir('.') if f.startswith('catalog_products_') and f.endswith('.csv')]
    if csv_files:
        latest_csv = max(csv_files)
        csv_path = latest_csv
        problematic_path = f"problematic_items_{latest_csv[16:-4]}.txt"
        
        # Read existing products
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                products.append(row)
                if row[2].startswith('Page '):
                    last_page = max(last_page, int(row[2].split(' ')[1]))
        
        # Read existing problematic items
        if os.path.exists(problematic_path):
            with open(problematic_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()[3:]  # Skip header
                problematic = [line.strip() for line in lines if line.strip()]
        
        print(f"Resuming from page {last_page + 1}")
        print(f"Found {len(products)} existing products")
        print(f"Found {len(problematic)} existing problematic items")
    
    # If no existing progress, create new files
    if not csv_path:
        csv_path = f"catalog_products_{timestamp}.csv"
        problematic_path = f"problematic_items_{timestamp}.txt"
    
    try:
        from pdf2image import convert_from_path
        # Process one page at a time with lower DPI and size
        for page_num, page in enumerate(convert_from_path(pdf_path, dpi=150, fmt='jpeg', thread_count=1, size=(1240, 1754)), 1):
            # Skip already processed pages
            if page_num <= last_page:
                continue
                
            print(f"\nProcessing page {page_num}")
            
            try:
                # Convert PIL Image to OpenCV format
                image = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                
                # Save debug image with compression
                debug_path = f"debug_page_{page_num}.jpg"  # Use jpg instead of png
                cv2.imwrite(debug_path, image, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                # Convert to grayscale
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                # Extract text regions
                product_regions = scraper.extract_text_regions(gray, is_product=True)
                price_regions = scraper.extract_text_regions(gray, is_product=False)
                
                print(f"Found {len(product_regions)} product regions and {len(price_regions)} price regions")
                
                # Process product regions
                page_products = []
                for region in product_regions:
                    text = scraper.extract_text_from_region(gray, region, is_product=True)
                    if text and len(text) > 10:  # Only process longer text that's likely a product name
                        # Look for price in the text
                        price_match = re.search(r'\$(\d+\.?\d{0,2})\s*(?:per\s*kg)?', text)
                        if price_match:
                            price = price_match.group(0)
                            product_name = text.replace(price, '').strip()
                            if product_name:
                                page_products.append([product_name, price, f"Page {page_num}"])
                        else:
                            # No price found in product text, mark as problematic
                            problematic.append(f"Page {page_num} - Product without price: {text}")
                
                # Process price regions
                for region in price_regions:
                    text = scraper.extract_text_from_region(gray, region, is_product=False)
                    price = scraper.extract_price(text)
                    if price:
                        # Try to find nearby product text
                        x, y, w, h = region
                        nearest_product = None
                        min_distance = float('inf')
                        
                        for prod_region in product_regions:
                            px, py, pw, ph = prod_region
                            distance = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                            if distance < min_distance:
                                min_distance = distance
                                nearest_product = scraper.extract_text_from_region(gray, prod_region, is_product=True)
                        
                        if nearest_product and len(nearest_product) > 10:
                            page_products.append([nearest_product, f"${price}", f"Page {page_num}"])
                        else:
                            problematic.append(f"Page {page_num} - Price without product: ${price}")
                
                products.extend(page_products)
                print(f"Found {len(page_products)} products on page {page_num}")
                
                # Save progress after each page
                with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Product", "Price", "Location"])
                    writer.writerows(products)
                
                with open(problematic_path, 'w', encoding='utf-8') as file:
                    file.write("Problematic Items:\n")
                    file.write("=================\n\n")
                    for item in problematic:
                        file.write(f"{item}\n")
                
            except Exception as e:
                print(f"Error processing page {page_num}: {str(e)}")
                problematic.append(f"Page {page_num} - Processing error: {str(e)}")
                continue
            finally:
                # Clean up memory
                try:
                    del image
                    del gray
                    del page
                    del page_products
                    del product_regions
                    del price_regions
                except:
                    pass
                import gc
                gc.collect()
    
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        return
    
    print(f"\nProcessing complete!")
    print(f"Total products found: {len(products)}")
    print(f"Problematic items: {len(problematic)}")
    print(f"Results saved to: {csv_path}")
    print(f"Problematic items saved to: {problematic_path}")

if __name__ == "__main__":
    main() 