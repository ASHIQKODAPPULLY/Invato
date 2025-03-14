import requests
import json
import csv
from datetime import datetime
import time
import random
import re

class WoolworthsScraper:
    def __init__(self):
        self.base_url = "https://www.woolworths.com.au"
        self.catalog_url = "https://www.woolworths.com.au/shop/catalogue"
        self.api_url = "https://www.woolworths.com.au/apis/ui/catalog/products"
        
        self.headers = {
            'authority': 'www.woolworths.com.au',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.woolworths.com.au',
            'referer': 'https://www.woolworths.com.au/shop/catalogue',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.csrf_token = None

    def get_csrf_token(self):
        """Get CSRF token from the catalog page"""
        try:
            response = self.session.get(self.catalog_url)
            response.raise_for_status()
            
            # Extract CSRF token from the page
            match = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', response.text)
            if match:
                self.csrf_token = match.group(1)
                self.session.headers['RequestVerificationToken'] = self.csrf_token
                print("Successfully obtained CSRF token")
                return True
            else:
                print("Could not find CSRF token")
                return False
                
        except Exception as e:
            print(f"Error getting CSRF token: {str(e)}")
            return False

    def get_catalog_products(self, page=1):
        """Get products from the current catalog"""
        try:
            data = {
                "catalogueId": None,  # Will be filled from the response
                "pageNumber": page,
                "pageSize": 100,
                "sortType": "CatalogueOrder",
                "filters": [],
                "isSpecial": True
            }
            
            # First get the current catalog ID
            response = self.session.get(self.catalog_url)
            response.raise_for_status()
            
            # Extract catalog ID from the page
            match = re.search(r'"catalogueId":"([^"]+)"', response.text)
            if match:
                data["catalogueId"] = match.group(1)
            else:
                print("Could not find catalog ID")
                return []
            
            # Get products from the catalog
            response = self.session.post(self.api_url, json=data)
            response.raise_for_status()
            
            result = response.json()
            return result.get('Products', [])
            
        except Exception as e:
            print(f"Error getting catalog products: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:200]}")
            return []

    def extract_product_info(self, product):
        """Extract relevant information from product data"""
        try:
            name = product.get('Name', '').strip()
            brand = product.get('Brand', '').strip()
            
            # Get price information
            price = product.get('Price', {})
            current_price = price.get('Now', 0)
            was_price = price.get('Was', 0)
            
            # Get savings information
            savings = price.get('SaveAmount', 0)
            savings_text = price.get('SaveText', '')
            
            # Get additional information
            cup_price = product.get('CupPrice', {})
            cup_measure = cup_price.get('CupMeasure', '')
            cup_price_text = cup_price.get('CupPriceText', '')
            
            package_size = product.get('PackageSize', '')
            
            # Get promotional information
            promo = product.get('PromotionText', '')
            
            # Get category information
            category = product.get('Category', {}).get('Name', '')
            subcategory = product.get('Category', {}).get('ParentCategory', {}).get('Name', '')
            
            return {
                'name': name,
                'brand': brand,
                'current_price': current_price,
                'was_price': was_price,
                'savings': savings,
                'savings_text': savings_text,
                'cup_measure': cup_measure,
                'cup_price': cup_price_text,
                'package_size': package_size,
                'promotion': promo,
                'category': category,
                'subcategory': subcategory,
                'store': 'woolworths'
            }
        except Exception as e:
            print(f"Error extracting product info: {str(e)}")
            return None

    def save_to_csv(self, products, filename=None):
        """Save products to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"woolworths_catalog_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'name', 'brand', 'current_price', 'was_price', 
                    'savings', 'savings_text', 'cup_measure', 'cup_price',
                    'package_size', 'promotion', 'category', 'subcategory', 'store'
                ])
                writer.writeheader()
                writer.writerows(products)
            print(f"Saved {len(products)} products to {filename}")
            return filename
        except Exception as e:
            print(f"Error saving to CSV: {str(e)}")
            return None

    def scrape_catalog(self, max_pages=5):
        """Scrape multiple pages of the catalog"""
        all_products = []
        
        # Get CSRF token first
        if not self.get_csrf_token():
            print("Failed to get CSRF token")
            return []
        
        for page in range(1, max_pages + 1):
            print(f"Scraping catalog page {page}...")
            
            products = self.get_catalog_products(page)
            if not products:
                print(f"No more products found on page {page}")
                break
            
            print(f"Found {len(products)} products on page {page}")
            
            for product in products:
                product_info = self.extract_product_info(product)
                if product_info:
                    all_products.append(product_info)
            
            # Add a small delay between requests
            time.sleep(random.uniform(2, 4))
        
        return all_products

def main():
    scraper = WoolworthsScraper()
    
    print("Starting Woolworths catalog scraper...")
    print("Fetching catalog products...")
    
    # Scrape products
    products = scraper.scrape_catalog(max_pages=5)
    
    if products:
        # Save to CSV
        filename = scraper.save_to_csv(products)
        if filename:
            print(f"\nScraping completed successfully!")
            print(f"Total products found: {len(products)}")
            print(f"Results saved to: {filename}")
    else:
        print("No products found or error occurred during scraping.")

if __name__ == "__main__":
    main() 