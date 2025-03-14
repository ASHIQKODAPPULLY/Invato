from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import time
import csv
from datetime import datetime

class WoolworthsSeleniumScraper:
    def __init__(self):
        # Initialize Chrome with basic options
        options = Options()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--start-maximized')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'})
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)
        
    def change_location(self, postcode):
        """Change store location using postcode"""
        try:
            # Wait for page to load completely
            time.sleep(5)
            
            # Try to find and click the location button
            try:
                location_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='store-finder-button']")
                location_button.click()
            except:
                try:
                    location_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Store Finder']")
                    location_button.click()
                except:
                    print("Could not find location button")
                    return False
            
            time.sleep(3)
            
            # Try to find and fill the postcode input
            try:
                postcode_input = self.driver.find_element(By.CSS_SELECTOR, "input[data-testid='search-store-input']")
            except:
                try:
                    postcode_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Suburb or Postcode']")
                except:
                    print("Could not find postcode input")
                    return False
            
            postcode_input.clear()
            postcode_input.send_keys(postcode)
            time.sleep(1)
            postcode_input.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Try to find and click the select store button
            try:
                store_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='select-store-button']")
                store_button.click()
            except:
                try:
                    store_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-automation='select-store-button']")
                    store_button.click()
                except:
                    print("Could not find store selection button")
                    return False
            
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"Error changing location to {postcode}: {str(e)}")
            return False
            
    def search_product(self, product_name):
        """Search for a product and return its details"""
        try:
            # Try to find and use the search box
            try:
                search_box = self.driver.find_element(By.CSS_SELECTOR, "input[data-testid='search-input']")
            except:
                try:
                    search_box = self.driver.find_element(By.CSS_SELECTOR, "input[data-automation='search-box']")
                except:
                    print("Could not find search box")
                    return {"name": product_name, "price": "Error"}
            
            search_box.clear()
            search_box.send_keys(product_name)
            time.sleep(1)
            search_box.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Try to find product details
            try:
                # Try different selectors for product name
                try:
                    name = self.driver.find_element(By.CSS_SELECTOR, "h3[data-testid='product-title']").text.strip()
                except:
                    try:
                        name = self.driver.find_element(By.CSS_SELECTOR, "h3.product-title").text.strip()
                    except:
                        name = product_name
                
                # Try different selectors for price
                try:
                    price = self.driver.find_element(By.CSS_SELECTOR, "div[data-testid='product-price']").text.strip()
                except:
                    try:
                        price = self.driver.find_element(By.CSS_SELECTOR, "div.product-price").text.strip()
                    except:
                        price = "Not Found"
                
                return {
                    "name": name,
                    "price": price
                }
            except:
                return {
                    "name": product_name,
                    "price": "Not Found"
                }
                
        except Exception as e:
            print(f"Error searching for {product_name}: {str(e)}")
            return {
                "name": product_name,
                "price": "Error"
            }
            
    def scrape_products(self, locations, products):
        """Scrape multiple products across multiple locations"""
        results = []
        
        try:
            # Open Woolworths website
            self.driver.get("https://www.woolworths.com.au")
            time.sleep(5)
            
            for location in locations:
                print(f"\nChecking prices in location: {location}")
                
                # Change location
                if not self.change_location(location):
                    print(f"Skipping location {location} due to error")
                    continue
                
                for product in products:
                    print(f"Searching for {product}...")
                    product_info = self.search_product(product)
                    results.append({
                        "location": location,
                        "product": product_info["name"],
                        "price": product_info["price"]
                    })
                    time.sleep(2)
                    
            return results
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return results
        finally:
            self.driver.quit()
            
    def save_results(self, results, filename=None):
        """Save results to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"woolworths_prices_{timestamp}.csv"
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["location", "product", "price"])
                writer.writeheader()
                writer.writerows(results)
            print(f"\nResults saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            return False

def main():
    # Configuration
    locations = ["2000", "3000", "4000", "5000"]  # Sydney, Melbourne, Brisbane, Adelaide
    products = [
        "Milk 2L",
        "Bread White",
        "Eggs 12 pack",
        "Banana 1kg",
        "Chicken Breast"
    ]
    
    print("Starting Woolworths price scraper...")
    print(f"Locations to check: {', '.join(locations)}")
    print(f"Products to search: {', '.join(products)}")
    
    # Initialize and run scraper
    scraper = WoolworthsSeleniumScraper()
    results = scraper.scrape_products(locations, products)
    
    # Save results
    if results:
        scraper.save_results(results)
        print("\nScraping completed successfully!")
    else:
        print("\nNo results were collected.")

if __name__ == "__main__":
    main() 