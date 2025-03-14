import http.server
import socketserver
import webbrowser
import os
import sys
import time
import traceback
import json
import requests
import csv
import io
import sqlite3
import smtplib
import threading
import schedule
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import parse_qs, urlparse

# Database initialization
def get_db_connection():
    try:
        conn = sqlite3.connect('prices.db')
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    try:
        conn = get_db_connection()
        if not conn:
            print("Failed to connect to database")
            return False
            
        c = conn.cursor()
        
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS prices
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      store TEXT,
                      product_name TEXT,
                      brand TEXT,
                      price REAL,
                      update_date TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      email TEXT,
                      frequency TEXT,
                      last_reminder TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS upload_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      store TEXT,
                      upload_date TEXT,
                      status TEXT,
                      products_updated INTEGER)''')
        
        # Verify if data exists
        c.execute('SELECT COUNT(*) FROM prices')
        count = c.fetchone()[0]
        print(f"\nCurrent products in database: {count}")
        
        # Insert sample data if the prices table is empty
        if count == 0:
            sample_data = [
                # Woolworths products
                ('woolworths', 'Milk (1L)', 'Devondale', 3.50, datetime.now().isoformat()),
                ('woolworths', 'Bread', 'Wonder White', 3.80, datetime.now().isoformat()),
                ('woolworths', 'Eggs (12)', 'Farm Fresh', 5.50, datetime.now().isoformat()),
                ('woolworths', 'Bananas (1kg)', 'Fresh', 4.90, datetime.now().isoformat()),
                ('woolworths', 'Rice (1kg)', 'SunRice', 4.00, datetime.now().isoformat()),
                
                # Coles products
                ('coles', 'Milk (1L)', 'Devondale', 3.55, datetime.now().isoformat()),
                ('coles', 'Bread', 'Wonder White', 3.70, datetime.now().isoformat()),
                ('coles', 'Eggs (12)', 'Farm Fresh', 5.60, datetime.now().isoformat()),
                ('coles', 'Bananas (1kg)', 'Fresh', 4.95, datetime.now().isoformat()),
                ('coles', 'Rice (1kg)', 'SunRice', 4.20, datetime.now().isoformat()),
                
                # Aldi products
                ('aldi', 'Milk (1L)', 'Farmdale', 3.25, datetime.now().isoformat()),
                ('aldi', 'Bread', 'Bakers Life', 3.49, datetime.now().isoformat()),
                ('aldi', 'Eggs (12)', 'Lodge Farm', 5.29, datetime.now().isoformat()),
                ('aldi', 'Bananas (1kg)', 'Fresh', 4.49, datetime.now().isoformat()),
                ('aldi', 'Rice (1kg)', 'Essentials', 3.99, datetime.now().isoformat())
            ]
            
            try:
                c.executemany('''INSERT INTO prices 
                                (store, product_name, brand, price, update_date)
                                VALUES (?, ?, ?, ?, ?)''', sample_data)
                
                # Add sample upload history
                c.execute('''INSERT INTO upload_history 
                            (store, upload_date, status, products_updated)
                            VALUES (?, ?, ?, ?)''',
                         ('all stores', datetime.now().isoformat(), 'Success', len(sample_data)))
                
                conn.commit()
                print(f"\nInitialized database with {len(sample_data)} products")
                
                # Verify data was inserted
                c.execute('SELECT COUNT(*) FROM prices')
                count = c.fetchone()[0]
                print(f"Verified products in database: {count}")
                
            except sqlite3.Error as e:
                print(f"Error inserting sample data: {e}")
                return False
        
        # Show some sample data
        try:
            c.execute('SELECT DISTINCT store, product_name, price FROM prices LIMIT 5')
            print("\nSample products available:")
            for row in c.fetchall():
                print(f"{row[0]}: {row[1]} - ${row[2]:.2f}")
        except sqlite3.Error as e:
            print(f"Error fetching sample data: {e}")
        
        conn.close()
        print("\nDatabase initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nError initializing database: {str(e)}")
        traceback.print_exc()
        return False

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
        # Initialize sample data
        self.sample_data = {
            'milk': {
                'woolworths': {'price': 3.50, 'last_updated': datetime.now().isoformat()},
                'coles': {'price': 3.75, 'last_updated': datetime.now().isoformat()},
                'aldi': {'price': 3.25, 'last_updated': datetime.now().isoformat()}
            },
            'bread': {
                'woolworths': {'price': 2.50, 'last_updated': datetime.now().isoformat()},
                'coles': {'price': 2.75, 'last_updated': datetime.now().isoformat()},
                'aldi': {'price': 2.25, 'last_updated': datetime.now().isoformat()}
            }
        }
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Override to provide more detailed logging"""
        print(f"\nRequest: {args[0]}")
        print(f"Status: {args[1]}")
        print(f"Size: {args[2]}")
        sys.stdout.flush()

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_csv_response(self, csv_content, filename):
        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(csv_content.encode('utf-8'))

    def generate_template_csv(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['name', 'brand', 'price'])
        example_products = [
            ['Milk (1L)', 'Devondale', '3.00'],
            ['Bread', 'Wonder White', '3.50'],
            ['Eggs (12)', 'Farm Fresh', '6.00'],
            ['Bananas (1kg)', 'Cavendish', '3.90']
        ]
        writer.writerows(example_products)
        return output.getvalue()

    def do_GET(self):
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            print(f"\nHandling request for: {path}")

            # API endpoints
            if path.startswith('/api/'):
                if path == '/api/prices':
                    query = parse_qs(parsed_path.query)
                    product_name = query.get('product', [''])[0].lower()
                    print(f"Searching for product: {product_name}")
                    
                    conn = sqlite3.connect('prices.db')
                    c = conn.cursor()
                    c.execute('''SELECT store, price, update_date 
                                FROM prices 
                                WHERE LOWER(product_name) LIKE ?''',
                             (f'%{product_name}%',))
                    results = c.fetchall()
                    conn.close()
                    
                    prices = {}
                    for store, price, update_date in results:
                        prices[store] = {
                            'price': price,
                            'last_updated': update_date
                        }
                    
                    print(f"Found prices: {prices}")
                    self.send_json_response(prices)
                    return

                elif path == '/api/cart-total':
                    query = parse_qs(parsed_path.query)
                    products = json.loads(query.get('products', ['[]'])[0])
                    print(f"Calculating total for products: {products}")
                    
                    conn = sqlite3.connect('prices.db')
                    c = conn.cursor()
                    
                    totals = {'woolworths': 0, 'coles': 0, 'aldi': 0}
                    for product in products:
                        c.execute('''SELECT store, price 
                                   FROM prices 
                                   WHERE LOWER(product_name) LIKE ?''',
                                (f'%{product.lower()}%',))
                        results = c.fetchall()
                        for store, price in results:
                            totals[store] += price
                    
                    conn.close()
                    print(f"Calculated totals: {totals}")
                    
                    self.send_json_response({
                        'totals': totals,
                        'best_value': min(totals.items(), key=lambda x: x[1])[0]
                    })
                    return

            # Special routes
            elif path == '/download-template':
                csv_content = self.generate_template_csv()
                self.send_csv_response(csv_content, 'price_template.csv')
                return

            # Static file handling
            else:
                if path == '/' or path == '':
                    self.path = '/index.html'
                elif path == '/admin':
                    self.path = '/admin.html'
                else:
                    self.path = path

                try:
                    return super().do_GET()
                except Exception as e:
                    print(f"Error serving static file: {e}")
                    self.send_error(404, "File not found")
                    return

        except Exception as e:
            print(f"\nError handling request: {str(e)}")
            traceback.print_exc()
            self.send_error(500, f"Internal server error: {str(e)}")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/upload-catalog':
            # Handle multipart form data for file upload
            # Parse the CSV and update the database
            try:
                # This is a simplified version - you'll need proper multipart form parsing
                csv_content = post_data.decode('utf-8')
                reader = csv.DictReader(io.StringIO(csv_content))
                
                conn = sqlite3.connect('prices.db')
                c = conn.cursor()
                
                products_updated = 0
                store = 'unknown'  # You'll need to get this from the form data
                
                for row in reader:
                    c.execute('''INSERT OR REPLACE INTO prices 
                                (store, product_name, brand, price, update_date)
                                VALUES (?, ?, ?, ?, ?)''',
                             (store, row['name'], row['brand'], float(row['price']), 
                              datetime.now().isoformat()))
                    products_updated += 1
                
                c.execute('''INSERT INTO upload_history 
                            (store, upload_date, status, products_updated)
                            VALUES (?, ?, ?, ?)''',
                         (store, datetime.now().isoformat(), 'Success', products_updated))
                
                conn.commit()
                conn.close()
                
                self.send_json_response({
                    'success': True,
                    'productsUpdated': products_updated
                })
                
            except Exception as e:
                self.send_json_response({
                    'success': False,
                    'error': str(e)
                })
                
        elif self.path == '/save-reminder-settings':
            try:
                settings = json.loads(post_data)
                
                conn = sqlite3.connect('prices.db')
                c = conn.cursor()
                c.execute('''INSERT INTO settings (email, frequency, last_reminder)
                            VALUES (?, ?, ?)''',
                         (settings['email'], settings['frequency'], 
                          datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                self.send_json_response({'success': True})
                
            except Exception as e:
                self.send_json_response({
                    'success': False,
                    'error': str(e)
                })
        else:
            self.send_response(404)
            self.end_headers()

def send_reminder_email():
    conn = sqlite3.connect('prices.db')
    c = conn.cursor()
    c.execute('SELECT email, frequency FROM settings ORDER BY id DESC LIMIT 1')
    settings = c.fetchone()
    
    if settings:
        email, frequency = settings
        
        # Get catalog status
        c.execute('''SELECT store, MAX(update_date) 
                    FROM prices 
                    GROUP BY store''')
        catalog_status = c.fetchall()
        
        # Compose email
        message = "Catalog Update Reminder\n\n"
        for store, last_update in catalog_status:
            days_old = (datetime.now() - datetime.fromisoformat(last_update)).days
            message += f"{store}: Last updated {days_old} days ago\n"
        
        # Send email (you'll need to configure your SMTP settings)
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                # server.login('your-email@gmail.com', 'your-password')
                
                msg = MIMEText(message)
                msg['Subject'] = 'Catalog Update Reminder'
                msg['From'] = 'your-email@gmail.com'
                msg['To'] = email
                
                # server.send_message(msg)
                print(f"Reminder email would be sent to {email}")
                
        except Exception as e:
            print(f"Error sending reminder email: {e}")
    
    conn.close()

def schedule_reminders():
    schedule.every().day.at("09:00").do(send_reminder_email)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_server():
    try:
        PORT = 8000
        Handler = PriceHandler
        
        print(f"\nInitializing database...")
        if not init_db():
            print("Failed to initialize database. Server will not start.")
            return
        
        print(f"\nTrying to start server on port {PORT}...")
        
        # Create the server with an empty string as hostname to accept connections from any IP
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"\nServer started successfully!")
            print(f"\nAccess the application:")
            print(f"1. Customer interface: http://localhost:{PORT}")
            print(f"2. Admin panel: http://localhost:{PORT}/admin")
            print("\nAvailable test products:")
            print("- milk")
            print("- bread")
            print("- eggs")
            print("- bananas")
            print("- rice")
            print("\nPress Ctrl+C to stop the server")
            print("\nWaiting for requests...")
            
            # Start the server
            httpd.serve_forever()
            
    except Exception as e:
        print(f"\nError starting server: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0) 