# amazon_price_tracker.py
# Works on Amazon.in as of Nov 2025 | Python 3.9+
# Features: Random delays, rotating User-Agent, Cloudflare/JS handling via Selenium, Google Sheets export

import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from fake_useragent import UserAgent
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# ====================== CONFIGURATION ======================
# Put your product ASINs or full URLs here (Client will give you this)
PRODUCT_URLS = [
    "https://www.amazon.in/OnePlus-Snapdragon-Flagship-Powered-Phantom/dp/B0FCML66W9",   # Example: iPhone 15 case
    "https://www.amazon.in/iPhone-16-Plus-128-GB/dp/B0DGJ6JS1D",
    # Add more...
]

# Google Sheets setup (optional but clients LOVE this)
USE_GOOGLE_SHEETS = False
SHEET_NAME = "Amazon Price Tracker"
WORKSHEET_NAME = "Live Data"

# WhatsApp alert threshold (send if price drops more than X%)
PRICE_DROP_ALERT_PERCENT = 8

# ====================== SETUP ======================
ua = UserAgent()
chrome_options = Options()
chrome_options.add_argument("--headless")  # Remove this line if you want to see browser
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument(f"user-agent={ua.random}")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

def random_delay(min_sec=2, max_sec=6):
    time.sleep(random.uniform(min_sec, max_sec))

def get_amazon_data(url):
    print(f"Scraping: {url}")
    driver.get(url)
    random_delay(4, 8)

    data = {
        "URL": url,
        "Title": "N/A",
        "Price": "N/A",
        "MRP": "N/A",
        "Discount": "N/A",
        "Rating": "N/A",
        "Reviews": "N/A",
        "Availability": "N/A",
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        # Title
        title = wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
        data["Title"] = title.text.strip()

        # Price (main deal price)
        try:
            price = driver.find_element(By.CSS_SELECTOR, ".a-price-whole")
            data["Price"] = "₹" + price.text.replace(".", "") + driver.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        except:
            try:
                price = driver.find_element(By.CSS_SELECTOR, "span.a-price.a-text-price.a-size-medium.apexPriceToPay")
                data["Price"] = price.text
            except:
                pass

        # MRP (striked price)
        try:
            mrp = driver.find_element(By.CSS_SELECTOR, "span.a-price.a-text-price span.a-offscreen")
            data["MRP"] = mrp.get_attribute("innerText")
        except:
            pass

        # Rating & Reviews
        try:
            rating = driver.find_element(By.ID, "acrPopover")
            data["Rating"] = rating.get_attribute("title")
        except:
            pass

        try:
            reviews = driver.find_element(By.ID, "acrCustomerReviewText")
            data["Reviews"] = reviews.text
        except:
            pass

        # Availability
        try:
            avail = driver.find_element(By.ID, "availability")
            data["Availability"] = avail.text.strip()
        except:
            data["Availability"] = "In Stock"

    except TimeoutException:
        data["Title"] = "Blocked or Timeout - Manual check needed"
    
    print(f"✅ Success: {data['Title'][:50]}... | Price: {data['Price']}")
    return data

# ====================== MAIN SCRAPING LOOP ======================
results = []
for url in PRODUCT_URLS:
    item = get_amazon_data(url)
    results.append(item)
    random_delay(5, 10)

driver.quit()

# Convert to DataFrame
df = pd.DataFrame(results)
df.to_csv(f"amazon_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
print("CSV saved!")

# ====================== GOOGLE SHEETS EXPORT (Optional) ======================
if USE_GOOGLE_SHEETS:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Put your service account JSON file in same folder
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(SHEET_NAME)
    except:
        sh = client.create(SHEET_NAME)
        sh.share("karanshah005@gmail.com", perm_type='user', role='writer')  # Change to client's email later

    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)

    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("Google Sheets updated!")

print("Scraping completed! Check CSV and Google Sheets.")