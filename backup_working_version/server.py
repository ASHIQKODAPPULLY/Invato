import http.server
import socketserver
import webbrowser
import os
import sys
import time
import traceback
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class PriceScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def scrape_woolworths(self, product_name):
        try:
            # Example URL - you would need to adjust this based on Woolworths' actual structure
            url = f'https://www.woolworths.com.au/shop/search/products?searchTerm={product_name}'
            response = requests.get(url, headers=self.headers)
            # Parse the response and extract price
            # This is a simplified example - actual implementation would need more robust parsing
            return {'price': 0.00, 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            print(f"Error scraping Woolworths: {e}")
            return None

    def scrape_coles(self, product_name):
        try:
            url = f'https://www.coles.com.au/search?q={product_name}'
            response = requests.get(url, headers=self.headers)
            # Parse the response and extract price
            return {'price': 0.00, 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            print(f"Error scraping Coles: {e}")
            return None

    def scrape_aldi(self, product_name):
        try:
            url = f'https://www.aldi.com.au/en/search/?text={product_name}'
            response = requests.get(url, headers=self.headers)
            # Parse the response and extract price
            return {'price': 0.00, 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            print(f"Error scraping Aldi: {e}")
            return None

class PriceHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.scraper = PriceScraper()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/prices'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Extract product name from query
            product_name = self.path.split('=')[1] if '=' in self.path else ''
            
            # Get prices from all stores
            prices = {
                'woolworths': self.scraper.scrape_woolworths(product_name),
                'coles': self.scraper.scrape_coles(product_name),
                'aldi': self.scraper.scrape_aldi(product_name)
            }
            
            self.wfile.write(json.dumps(prices).encode())
        else:
            super().do_GET()

def start_server():
    try:
        PORT = 8000
        Handler = PriceHandler
        
        print(f"\nTrying to start server on port {PORT}...")
        
        # Create the server
        httpd = socketserver.TCPServer(("localhost", PORT), Handler)
        
        print(f"\nServer started successfully!")
        print(f"Access the application at: http://localhost:{PORT}")
        print("\nPress Ctrl+C to stop the server")
        
        # Try to open the browser
        try:
            print("\nOpening browser...")
            webbrowser.open(f'http://localhost:{PORT}')
        except Exception as e:
            print(f"\nCould not open browser automatically: {str(e)}")
            print(f"Please open your browser and go to: http://localhost:{PORT}")
        
        # Start the server
        print("\nServer is running...")
        httpd.serve_forever()
        
    except Exception as e:
        print(f"\nDetailed error information:")
        print("="*50)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("="*50)
        print("\nTroubleshooting steps:")
        print("1. Make sure no other application is using port 8000")
        print("2. Try running the script as administrator")
        print("3. Check if your firewall is blocking the connection")
        print("4. Install required packages: pip install requests beautifulsoup4")
        
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    print("\nStarting price comparison server...")
    print("Note: Real-time price scraping requires proper API access or agreements with retailers")
    print("This is a demonstration version with placeholder scraping functionality")
    
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0) 