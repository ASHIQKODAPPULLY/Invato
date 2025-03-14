from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import random
from datetime import datetime

class WoolworthsScraper:
    def __init__(self):
        # Setup Selenium WebDriver with additional options for stability
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")  # Run without opening a browser
        self.options.add_argument("--disable-gpu")  # Required for headless mode
        self.options.add_argument("--window-size=1920x1080")  # Ensure full rendering
        self.options.add_argument("--no-sandbox")  # Bypass OS security model
        self.options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        self.options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation
        
        # Add random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        self.options.add_argument(f"user-agent={random.choice(user_agents)}")
        
        # Initialize WebDriver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.wait = WebDriverWait(self.driver, 10)  # Wait up to 10 seconds for elements

    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add random delay between actions to appear more human-like"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def scrape_product(self, search_term, max_pages=3):
        """Scrape product data for a given search term"""
        base_url = "https://www.woolworths.com.au/"
        self.driver.get(base_url)
        self.random_delay(3, 6)  # Longer delay for initial page load

        try:
            # Wait for search box and enter search term
            search_box = self.wait.until(
                EC.presence_of_element_located((By.NAME, "search"))
            )
            search_box.clear()
            search_box.send_keys(search_term)
            search_box.send_keys(Keys.RETURN)
            self.random_delay()

            product_list = []
            page = 1

            while page <= max_pages:
                print(f"Processing page {page} for {search_term}...")
                self.random_delay()

                # Wait for products to load
                self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-title-link"))
                )

                # Extract product information
                products = self.driver.find_elements(By.CSS_SELECTOR, ".product-title-link")
                prices = self.driver.find_elements(By.CSS_SELECTOR, ".price")

                for i in range(len(products)):
                    try:
                        product_name = products[i].text.strip()
                        price_text = prices[i].text.strip()
                        
                        if product_name and price_text:
                            product_list.append({
                                "search_term": search_term,
                                "product": product_name,
                                "price": price_text,
                                "page": page,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                    except Exception as e:
                        print(f"Error extracting product {i}: {str(e)}")
                        continue

                # Try to go to next page
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Next page']")
                    if not next_button.is_enabled():
                        break
                    next_button.click()
                    page += 1
                    self.random_delay(3, 6)  # Longer delay between pages
                except Exception as e:
                    print(f"No more pages available: {str(e)}")
                    break

            return product_list

        except Exception as e:
            print(f"Error scraping {search_term}: {str(e)}")
            return []

    def save_to_csv(self, data, filename):
        """Save data to CSV file"""
        if not data:
            return
            
        fieldnames = ["search_term", "product", "price", "page", "timestamp"]
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to CSV: {str(e)}")

    def scrape_multiple_products(self, search_terms, max_pages=3):
        """Scrape multiple products and save results"""
        all_data = []
        
        try:
            for term in search_terms:
                print(f"\nScraping {term}...")
                products = self.scrape_product(term, max_pages)
                all_data.extend(products)
                
                # Save progress after each search term
                progress_file = f"woolworths_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                self.save_to_csv(all_data, progress_file)
                print(f"Found {len(products)} products for {term}")
                
                # Random delay between searches
                self.random_delay(5, 10)
            
            return all_data
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return all_data
        
        finally:
            self.driver.quit()

def main():
    # List of products to search
    search_terms = [
        "milk", "bread", "eggs", "cheese", "chicken",
        "rice", "pasta", "fruit", "vegetables", "meat"
    ]
    
    # Initialize scraper
    scraper = WoolworthsScraper()
    
    # Start scraping
    print("Starting Woolworths price scraper...")
    results = scraper.scrape_multiple_products(search_terms, max_pages=3)
    
    # Save final results
    output_file = f"woolworths_prices_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    scraper.save_to_csv(results, output_file)
    
    print(f"\nScraping complete!")
    print(f"Total products found: {len(results)}")
    print(f"Data saved to: {output_file}")

if __name__ == "__main__":
    main() 