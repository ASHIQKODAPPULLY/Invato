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
        
        # Define expected screenshot dimensions and regions
        self.template = {
            'width': 1876,  # Match your screenshot width
            'height': 355,  # Match your screenshot height
            'product_regions': [
                # Format: [x1, y1, x2, y2] in percentages of image dimensions
                [5, 10, 60, 90],  # Product name and description (left side)
            ],
            'price_regions': [
                [60, 10, 95, 45],  # Original price region (right side top)
                [60, 55, 95, 90],  # Sale price region (right side bottom)
            ]
        }
        
        self.price_patterns = [
            r"\$\s*(\d+\.?\d{0,2})",  # Standard price format ($XX.XX)
            r"(\d+\.?\d{0,2})\s*\$",  # Price with $ at end
            r"SAVE.*?\$(\d+\.?\d{0,2})",  # Price after SAVE
            r"\$(\d+\.?\d{0,2})\s*(?:ea|each)?",  # Price with optional ea/each
            r"(\d+\.?\d{0,2})",  # Just numbers that look like prices
        ]
        
    def create_template_guide(self, output_path="screenshot_template.png"):
        """Create a visual guide for taking screenshots"""
        # Create a blank image with template dimensions
        template = np.ones((self.template['height'], self.template['width'], 3), dtype=np.uint8) * 255
        
        # Draw product regions in green
        for region in self.template['product_regions']:
            x1 = int(region[0] * self.template['width'] / 100)
            y1 = int(region[1] * self.template['height'] / 100)
            x2 = int(region[2] * self.template['width'] / 100)
            y2 = int(region[3] * self.template['height'] / 100)
            cv2.rectangle(template, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(template, "Product Region", (x1+10, y1+30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Draw price regions in blue
        for region in self.template['price_regions']:
            x1 = int(region[0] * self.template['width'] / 100)
            y1 = int(region[1] * self.template['height'] / 100)
            x2 = int(region[2] * self.template['width'] / 100)
            y2 = int(region[3] * self.template['height'] / 100)
            cv2.rectangle(template, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(template, "Price Region", (x1+10, y1+30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Add instructions
        instructions = [
            "Screenshot Template Guide:",
            "1. Each product should be captured in a single wide screenshot",
            "2. Product name and details should be in the green region (left)",
            "3. Prices should be in the blue regions (right)",
            "4. Take screenshot using Win+Shift+S",
            f"Recommended size: {self.template['width']}x{self.template['height']} pixels"
        ]
        
        y = 30
        for instruction in instructions:
            cv2.putText(template, instruction, (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            y += 30
        
        # Save template guide
        cv2.imwrite(output_path, template)
        print(f"Template guide saved to: {output_path}")
        return output_path

    def validate_screenshot(self, image):
        """Validate if screenshot matches the template requirements"""
        height, width = image.shape[:2]
        
        # Check if dimensions are within 20% of expected
        width_diff = abs(width - self.template['width']) / self.template['width']
        height_diff = abs(height - self.template['height']) / self.template['height']
        
        if width_diff > 0.2 or height_diff > 0.2:
            print(f"Warning: Image dimensions ({width}x{height}) differ significantly from template ({self.template['width']}x{self.template['height']})")
            print("Consider resizing your browser window to match the template")
            
            # Resize image to template dimensions
            image = cv2.resize(image, (self.template['width'], self.template['height']))
            print(f"Image has been resized to match template dimensions")
        
        return image

    def get_template_regions(self, image):
        """Get regions based on template percentages"""
        height, width = image.shape[:2]
        
        product_regions = []
        for region in self.template['product_regions']:
            x1 = int(region[0] * width / 100)
            y1 = int(region[1] * height / 100)
            x2 = int(region[2] * width / 100)
            y2 = int(region[3] * height / 100)
            product_regions.append((x1, y1, x2-x1, y2-y1))
        
        price_regions = []
        for region in self.template['price_regions']:
            x1 = int(region[0] * width / 100)
            y1 = int(region[1] * height / 100)
            x2 = int(region[2] * width / 100)
            y2 = int(region[3] * height / 100)
            price_regions.append((x1, y1, x2-x1, y2-y1))
        
        return product_regions, price_regions

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
        
    def clean_product_text(self, text):
        """Clean up product text"""
        # Remove common noise phrases
        noise_phrases = [
            'Promoted',
            'SAVE',
            'yippee',
            'Sua',
            'needs',
            '/ 100g',
            '/ 1006',
            'Chilled essentials for your',
            'eee',
            'ae',
            'ne',
            'aan',
            'idj',
            '3.01'
        ]
        
        # First convert to lowercase for better matching
        text = text.lower()
        
        # Remove noise phrases (case insensitive)
        for phrase in noise_phrases:
            text = re.sub(re.escape(phrase.lower()), '', text)
        
        # Remove price-like patterns
        text = re.sub(r'\$?\s*\d+\.?\d{0,2}\s*(?:per\s*kg)?', '', text)
        text = re.sub(r'\d+\s*-\s*\d+\.?\d{0,2}', '', text)
        text = re.sub(r'\d+\.?\d{0,2}\s*-\s*\$?\d+\.?\d{0,2}', '', text)
        
        # Clean up the text
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        text = re.sub(r'[^\w\s\-\.]', '', text)  # Keep only word chars, spaces, dots and hyphens
        text = text.strip()
        
        # Capitalize words
        text = ' '.join(word.capitalize() for word in text.split())
        
        # Remove any remaining numbers at the start/end
        text = re.sub(r'^\d+\s*', '', text)
        text = re.sub(r'\s*\d+$', '', text)
        
        return text

    def extract_price(self, text):
        """Extract price from text using multiple patterns"""
        # First try to find prices with dollar signs
        price_patterns = [
            r"\$\s*(\d+\.?\d{0,2})",  # Standard price format ($XX.XX)
            r"(\d+\.?\d{0,2})\s*\$",  # Price with $ at end
            r"SAVE.*?\$(\d+\.?\d{0,2})",  # Price after SAVE
            r"\$(\d+\.?\d{0,2})\s*(?:ea|each)?",  # Price with optional ea/each
            r"(\d+\.?\d{0,2})",  # Just numbers that look like prices
        ]
        
        # First look for "SAVE" amounts
        save_match = re.search(r'SAVE.*?\$(\d+\.?\d{0,2})', text)
        if save_match:
            try:
                save_amount = float(save_match.group(1))
                # Look for the original price
                price_match = re.search(r'\$(\d+\.?\d{0,2})', text.replace(save_match.group(0), ''))
                if price_match:
                    original_price = float(price_match.group(1))
                    # Calculate the sale price
                    sale_price = original_price - save_amount
                    if 0.01 <= sale_price <= 1000:
                        return f"{sale_price:.2f}"
            except ValueError:
                pass
        
        # Try regular price patterns
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Convert to float and format to 2 decimal places
                    price = float(matches[0])
                    # Filter out unreasonable prices
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

    def process_image(self, image_path, source_name="Unknown"):
        """Process a single image file and return found products"""
        print(f"\nProcessing image: {image_path}")
        products = []
        problematic = []

        try:
            # Read image
            if isinstance(image_path, str):
                image = cv2.imread(image_path)
            else:
                image = image_path  # Already a numpy array

            if image is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Validate and adjust screenshot
            image = self.validate_screenshot(image)

            # Save original debug image
            debug_path = f"debug_image_original_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(debug_path, image, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # Image preprocessing
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Increase contrast
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            
            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(binary)
            
            # Save preprocessed debug image
            debug_path = f"debug_image_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(debug_path, denoised, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # Get template-based regions
            product_regions, price_regions = self.get_template_regions(denoised)

            print(f"Processing {len(product_regions)} product regions and {len(price_regions)} price regions")

            # Process product regions
            for region in product_regions:
                x, y, w, h = region
                # Extract region from both original and processed images
                roi_orig = image[y:y+h, x:x+w]
                roi_proc = denoised[y:y+h, x:x+w]
                
                # Try OCR on both versions
                text_orig = pytesseract.image_to_string(
                    roi_orig,
                    config='--oem 3 --psm 6',
                    lang='eng'
                ).strip()
                
                text_proc = pytesseract.image_to_string(
                    roi_proc,
                    config='--oem 3 --psm 6',
                    lang='eng'
                ).strip()
                
                # Use the longer text (usually more complete)
                text = text_orig if len(text_orig) > len(text_proc) else text_proc
                
                if text:
                    # Clean up the text
                    text = self.clean_product_text(text)
                    
                    if len(text) > 5:  # Minimum length after cleaning
                        # Look for price in the text
                        price = self.extract_price(text)
                        if price:
                            # Remove price from product name
                            product_name = re.sub(r'\$\s*\d+\.?\d{0,2}', '', text).strip()
                            if product_name:
                                products.append([product_name, f"${price}", source_name])
                        else:
                            # No price found in product text, mark as problematic
                            problematic.append(f"{source_name} - Product without price: {text}")

            # Process price regions
            for region in price_regions:
                x, y, w, h = region
                # Extract region from both original and processed images
                roi_orig = image[y:y+h, x:x+w]
                roi_proc = denoised[y:y+h, x:x+w]
                
                # Try OCR on both versions with different PSM modes
                configs = [
                    '--oem 3 --psm 7',  # Single line
                    '--oem 3 --psm 8',  # Single word
                    '--oem 3 --psm 6'   # Uniform block
                ]
                
                price = None
                for config in configs:
                    if price:
                        break
                        
                    text_orig = pytesseract.image_to_string(
                        roi_orig,
                        config=config,
                        lang='eng'
                    ).strip()
                    
                    text_proc = pytesseract.image_to_string(
                        roi_proc,
                        config=config,
                        lang='eng'
                    ).strip()
                    
                    # Try to extract price from both versions
                    price = self.extract_price(text_orig)
                    if not price:
                        price = self.extract_price(text_proc)

                if price:
                    # Try to find nearby product text
                    nearest_product = None
                    min_distance = float('inf')
                    max_distance = 300  # Maximum pixel distance to consider

                    for prod_region in product_regions:
                        px, py, pw, ph = prod_region
                        distance = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                        if distance < min_distance and distance < max_distance:
                            min_distance = distance
                            # Extract region from both original and processed images
                            prod_roi_orig = image[py:py+ph, px:px+pw]
                            prod_roi_proc = denoised[py:py+ph, px:px+pw]
                            
                            # Try OCR on both versions
                            prod_text_orig = pytesseract.image_to_string(
                                prod_roi_orig,
                                config='--oem 3 --psm 6',
                                lang='eng'
                            ).strip()
                            
                            prod_text_proc = pytesseract.image_to_string(
                                prod_roi_proc,
                                config='--oem 3 --psm 6',
                                lang='eng'
                            ).strip()
                            
                            # Use the longer text and clean it
                            text = prod_text_orig if len(prod_text_orig) > len(prod_text_proc) else prod_text_proc
                            nearest_product = self.clean_product_text(text)

                    if nearest_product and len(nearest_product) > 5:
                        products.append([nearest_product, f"${price}", source_name])
                    else:
                        problematic.append(f"{source_name} - Price without product: ${price}")

        except Exception as e:
            print(f"Error processing image: {str(e)}")
            problematic.append(f"{source_name} - Processing error: {str(e)}")

        finally:
            # Clean up memory
            try:
                del image
                del gray
                del binary
                del denoised
            except:
                pass
            import gc
            gc.collect()

        return products, problematic

def main():
    # Initialize scraper
    scraper = CatalogScraper()
    
    # Create template guide
    template_path = scraper.create_template_guide()
    print(f"\nA template guide has been created at: {template_path}")
    print("Please use this guide to take consistent screenshots.")
    print("\nInstructions:")
    print("1. Open the template guide image")
    print("2. Resize your browser window to match the template dimensions")
    print("3. Position the product information within the green regions")
    print("4. Position the prices within the blue regions")
    print("5. Take the screenshot using Win+Shift+S")
    print("6. Save the screenshot and process it with this script")
    
    # Ask if user wants to process an image
    response = input("\nWould you like to process a screenshot now? (y/n): ")
    if response.lower() != 'y':
        return
    
    # Get image path
    image_path = input("\nEnter the path to your screenshot: ")
    if not image_path:
        image_path = r"C:\Users\ashiq\OneDrive\Desktop\Business\apps\Screenshot 2025-03-10 034051.png"
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    # Get timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = f"extracted_products_{timestamp}.csv"
    problematic_path = f"problematic_items_{timestamp}.txt"
    
    print(f"\nProcessing image: {image_path}")
    
    # Process the image
    products, problematic = scraper.process_image(image_path, os.path.basename(image_path))
    
    # Save results
    save_progress(csv_path, problematic_path, products, problematic)
    
    print(f"\nProcessing complete!")
    print(f"Total products found: {len(products)}")
    print(f"Problematic items: {len(problematic)}")
    print(f"Results saved to: {csv_path}")
    print(f"Problematic items saved to: {problematic_path}")

def save_progress(csv_path, problematic_path, products, problematic):
    """Save current progress to files"""
    # Save products to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Product", "Price", "Source"])
        writer.writerows(products)
    
    # Save problematic items
    with open(problematic_path, 'w', encoding='utf-8') as file:
        file.write("Problematic Items:\n")
        file.write("=================\n\n")
        for item in problematic:
            file.write(f"{item}\n")

if __name__ == "__main__":
    main() 