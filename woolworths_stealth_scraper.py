import time
import random
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Bright Data proxy configuration
BRIGHT_DATA_USERNAME = "brd-customer-hl_1e069701-zone-web_unlocker1"
BRIGHT_DATA_PASSWORD = "1e069701eafa28"
BRIGHT_DATA_HOST = "brd.superproxy.io:22225"
PROXY = f"http://{BRIGHT_DATA_USERNAME}:{BRIGHT_DATA_PASSWORD}@{BRIGHT_DATA_HOST}"

def get_driver():
    """Initialize and return a configured Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--proxy-server={PROXY}")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Add user agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # Additional stealth settings
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        print(f"Driver initialization error: {str(e)}")
        raise

def scrape_woolworths(search_term, max_pages=3, max_retries=3):
    """Scrape Woolworths website for products with retry mechanism"""
    print(f"\nScraping: {search_term}...")
    
    for attempt in range(max_retries):
        try:
            driver = get_driver()
            print(f"Navigating to Woolworths website (Attempt {attempt + 1}/{max_retries})...")
            driver.get("https://www.woolworths.com.au/")
            time.sleep(random.uniform(3, 6))
            
            # Handle cookie consent if present
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".cookie-consent-button"))
                )
                cookie_button.click()
                print("Handled cookie consent popup")
            except:
                print("No cookie consent popup found")
            
            # Search for product
            try:
                print("Looking for search box...")
                search_box = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search']"))
                )
                print("Found search box, entering search term...")
                search_box.clear()
                
                # Type like a human
                for char in search_term:
                    search_box.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.2))
                
                time.sleep(random.uniform(0.5, 1))
                search_box.send_keys(Keys.RETURN)
                print("Search submitted")
            except TimeoutException as e:
                print(f"Error: Search bar not found: {str(e)}")
                print(f"Current page source: {driver.page_source[:500]}...")
                driver.quit()
                continue
            
            time.sleep(random.uniform(4, 7))
            product_list = []
            
            for page in range(max_pages):
                print(f"\nProcessing page {page + 1}...")
                
                # Simulate human scrolling
                scroll_height = random.randint(300, 700)
                driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                time.sleep(random.uniform(1, 2))
                scroll_height = random.randint(800, 1200)
                driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                time.sleep(random.uniform(1, 3))
                
                try:
                    print("Looking for product containers...")
                    product_containers = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product-tile-v2"))
                    )
                    print(f"Found {len(product_containers)} product containers")
                    
                    for container in product_containers:
                        try:
                            # Extract product details
                            product_name = container.find_element(By.CSS_SELECTOR, ".product-title-link").text.strip()
                            
                            # Handle different price formats
                            try:
                                price_element = container.find_element(By.CSS_SELECTOR, ".price-dollars")
                                cents_element = container.find_element(By.CSS_SELECTOR, ".price-cents")
                                price = f"${price_element.text}.{cents_element.text}"
                            except:
                                try:
                                    price = container.find_element(By.CSS_SELECTOR, ".primary").text.strip()
                                except:
                                    price = "N/A"
                            
                            # Get additional product information
                            try:
                                package_size = container.find_element(By.CSS_SELECTOR, ".package-size").text.strip()
                            except:
                                package_size = "N/A"
                                
                            try:
                                unit_price = container.find_element(By.CSS_SELECTOR, ".unit-price").text.strip()
                            except:
                                unit_price = "N/A"
                            
                            print(f"Found product: {product_name} - {price}")
                            product_list.append({
                                "Search Term": search_term,
                                "Product": product_name,
                                "Price": price,
                                "Package Size": package_size,
                                "Unit Price": unit_price,
                                "Store": "Woolworths",
                                "Date": datetime.now().strftime("%Y-%m-%d")
                            })
                            
                        except NoSuchElementException as e:
                            print(f"Error extracting product data: {str(e)}")
                            continue
                            
                except TimeoutException as e:
                    print(f"Error: No products found on page {page + 1}: {str(e)}")
                    break
                
                # Try next page
                try:
                    print("Looking for next page button...")
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Next page']"))
                    )
                    
                    if next_button.is_enabled():
                        print("Clicking next page...")
                        driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(random.uniform(1, 2))
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(random.uniform(4, 7))
                    else:
                        print("Next page button is disabled")
                        break
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
                    print(f"No more pages or navigation issue: {str(e)}")
                    break
            
            driver.quit()
            return product_list
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            if 'driver' in locals():
                driver.quit()
            if attempt < max_retries - 1:
                delay = random.uniform(5, 10)
                print(f"Waiting {delay:.2f}s before retrying...")
                time.sleep(delay)
            else:
                print(f"Failed to scrape {search_term} after {max_retries} attempts")
                return []

def run_scraper(search_terms, max_pages=3):
    """Run the scraper with rate limiting"""
    all_data = []
    
    for term in search_terms:
        results = scrape_woolworths(term, max_pages)
        print(f"\nFound {len(results)} products for {term}")
        all_data.extend(results)
        
        # Rate limiting between searches
        if term != search_terms[-1]:  # Don't wait after the last term
            delay = random.uniform(10, 20)
            print(f"Waiting {delay:.2f}s before next search...")
            time.sleep(delay)
    
    return all_data

if __name__ == "__main__":
    try:
        # List of products to search
        search_terms = ["milk", "bread", "eggs", "cheese", "chicken"]
        
        print("Starting Woolworths price scraper...")
        all_data = run_scraper(search_terms)
        
        # Save to CSV with timestamp
        if all_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"woolworths_prices_{timestamp}.csv"
            
            fieldnames = ["Search Term", "Product", "Price", "Package Size", "Unit Price", "Store", "Date"]
            print(f"\nSaving {len(all_data)} products to {filename}")
            
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_data)
            print(f"Data successfully saved to {filename}")
        else:
            print("\nNo data was collected during scraping")
            
    except Exception as e:
        print(f"\nCritical error in main execution: {str(e)}")
    
    finally:
        print("\nScript completed") 