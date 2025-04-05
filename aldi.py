import requests
import xlwt
from datetime import datetime, timedelta
import os
import imghdr

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import sqlite3

import sys

sys.path.append("../..")
from google_shopping_api import get_products, create_database_table

base_url = "https://www.aldi.com"
section_id = 1
page = 1
products = []
product_links = []

categories = [
    "https://www.instacart.com/store/aldi/collections/produce",
    "https://www.instacart.com/store/aldi/collections/meat-and-seafood",
    "https://www.instacart.com/store/aldi/collections/snacks-and-candy",
    "https://www.instacart.com/store/aldi/collections/frozen",
    "https://www.instacart.com/store/aldi/collections/dairy",
    "https://www.instacart.com/store/aldi/collections/beverages",
    "https://www.instacart.com/store/aldi/collections/3095-prepared-foods",
    "https://www.instacart.com/store/aldi/collections/baked-goods",
    "https://www.instacart.com/store/aldi/collections/3089-deli",
    "https://www.instacart.com/store/aldi/collections/canned-goods",
    "https://www.instacart.com/store/aldi/collections/household",
    "https://www.instacart.com/store/aldi/collections/dry-goods-pasta",
    "https://www.instacart.com/store/aldi/collections/oils-vinegars-spices",
    "https://www.instacart.com/store/aldi/collections/condiments-sauces",
    "https://www.instacart.com/store/aldi/collections/breakfast-foods",
    "https://www.instacart.com/store/aldi/collections/baking-essentials",
    "https://www.instacart.com/store/aldi/collections/pets",
    "https://www.instacart.com/store/aldi/collections/857-miscellaneous-grocery",
    "https://www.instacart.com/store/aldi/collections/kitchen-supplies",
    "https://www.instacart.com/store/aldi/collections/10235-wine",
    "https://www.instacart.com/store/aldi/collections/personal-care",
    "https://www.instacart.com/store/aldi/collections/baby",
    "https://www.instacart.com/store/aldi/collections/health-care",
    "https://www.instacart.com/store/aldi/collections/party-gifts",
    "https://www.instacart.com/store/aldi/collections/office-craft",
    "https://www.instacart.com/store/aldi/collections/10263-hard-beverages",
    "https://www.instacart.com/store/aldi/collections/floral",
    "https://www.instacart.com/store/aldi/collections/10242-beer-cider",
    "https://www.instacart.com/store/aldi/collections/10255-liquor",
    "https://www.instacart.com/store/aldi/collections/dynamic_collection-sales",
    "https://www.instacart.com/store/aldi/collections/n-charcuterie-22942",
    "https://www.instacart.com/store/aldi/collections/rc-2024-aldi-fan-favorites",
    "https://www.instacart.com/store/aldi/collections/n-toys-33913",
    "https://www.instacart.com/store/aldi/collections/n-shop-now-91665",
    "https://www.instacart.com/store/aldi/collections/n-vegan-27620",
    "https://www.instacart.com/store/aldi/collections/n-organic-90933",
    "https://www.instacart.com/store/aldi/collections/n-aldi-finds-limited-time-53509"
]

category_titles = [
    "Produce",
    "Meat & Seafood",
    "Snacks & Candy",
    "Frozen",
    "Dairy & Eggs",
    "Beverages",
    "Prepared Foods",
    "Bakery",
    "Deli",
    "Canned Goods & Soups",
    "Household",
    "Dry Goods & Pasta",
    "Oils, Vinegars, & Spices",
    "Condiments & Sauces",
    "Breakfast",
    "Baking Essentials",
    "Pets",
    "Miscellaneous",
    "Kitchen Supplies",
    "Wine",
    "Personal Care",
    "Baby",
    "Health Care",
    "Party & Gift Supplies",
    "Office & Craft",
    "Hard Beverages",
    "Floral",
    "Beer",
    "Liquor",
    "Sales",
    "Charcuterie",
    "2024 ALDI Fan Favorites",
    "Toys",
    "Shop Now",
    "Vegan",
    "Organic",
    "ALDI Finds (Limited Time)"
]

def is_relative_url(string):
    # Check if the string starts with '/' and matches a valid URL path
    pattern = r"^\/([a-z0-9\-._~!$&'()*+,;=:%]+\/?)*$"
    return bool(re.match(pattern, string))

def scroll_to_bottom_multiple_times(driver, scroll_pause_time=2, max_scrolls=10):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < max_scrolls:
        # Scroll down to the bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)  # Wait for new content to load

        # Calculate new scroll height and check if we've reached the bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # Exit loop if no new content loads
        last_height = new_height
        scroll_count += 1

def insert_product_record(db_name, table_name, record):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    insert_query = f"""
    INSERT INTO {table_name} (store_page_link, product_item_page_link, platform, store, product_name, price, image_file_name, image_link, product_rating, product_review_number, score)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.execute(insert_query, record)
    conn.commit()
    conn.close()

def get_product_list(driver, db_name, table_name, current_time, prefix):
    global section_id, categories
    num = 0
    # driver.get(categories[0])
    # driver.execute_script("document.body.style.zoom='25%'")
    # time.sleep(120)

    for category in categories:
        driver.get(category)
        driver.execute_script("document.body.style.zoom='80%'")
        scroll_to_bottom_multiple_times(driver, 2, 50)
        time.sleep(5)
        elements = driver.find_elements(By.XPATH, "//div[@aria-label='Product']")
        print(elements)
        for element in elements:

            image_url = ""
            title = ""
            rating = ""
            rating_count = ""
            product_link = ""
            price = ""
            download_url = ""
            weight = ""

            driver.execute_script("arguments[0].scrollIntoView();", element)

            try:
                img_element = element.find_element(By.TAG_NAME, "img")
                image_url = img_element.get_attribute("srcset").split(", ")[0]
            except:
                image_url = ""
            
            if(image_url):
                try:
                    responseImage = requests.get(image_url)
                    image_type = imghdr.what(None, responseImage.content)
                    if responseImage.status_code == 200:
                        img_url = "products/"+current_time+"/images/"+prefix+str(section_id)+'.'+image_type
                        with open(img_url, 'wb') as file:
                            file.write(responseImage.content)
                            download_url = img_url
                    # download_url = "products/"+current_time+"/images/"+prefix+str(section_id)+'.'+"jpg"
                except Exception as e:
                    print(e)
            try:
                title_element = element.find_element(By.CLASS_NAME, "e-1pnf8tv")
                title = title_element.text.strip()
            except:
                title = ""

            try:
                weight_element = element.find_element(By.CLASS_NAME, "e-zjik7")
                weight = weight_element.text.strip()
            except:
                weight = ""
            
            try:
                product_link_element = element.find_element(By.TAG_NAME, "a")
                product_link = product_link_element.get_attribute("href")
            except:
                product_link = ""

            try:
                informations = element.find_element(By.CLASS_NAME, "screen-reader-only").text
                price_splits = informations.split(":")
                price = price_splits[1].strip()
            except:
                price = ""

            record = [
                str(section_id),
                "https://instacart.com",
                product_link,
                "Instacart",
                category_titles[num],
                "",
                title,
                weight,
                "",
                price,
                download_url,
                image_url,
                "",
                "",
                rating,
                rating_count,
                "50 Beale St # 600, San Francisco, California 94105, US",
                "+18882467822",
                "37.7914",
                "122.3960",
                "",
            ]
            
            products.append(record)
            print(record)

            db_record = (
                "https://instacart.com",
                "https://instacart.com"+product_link,
                "Instacart",
                "Aldi",
                title,
                price,
                download_url,
                image_url,
                rating,
                rating_count,
                ""
            )

            insert_product_record(db_name, table_name, db_record)

            section_id = section_id + 1
            if(section_id > 50):
                break
        num = num + 1
        break
    
    return products

def get_aldi_products(db_name, table_name, store, current_time, prefix):
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  # Enable headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--start-maximized")  # Debugging support
    driver = uc.Chrome(options=options)
    
    # Create directories if they don't exist
    if not os.path.isdir("products"):
        os.mkdir("products")
    if not os.path.isdir(f"products/{current_time}"):
        os.mkdir(f"products/{current_time}")
    if not os.path.isdir(f"products/{current_time}/images"):
        os.mkdir(f"products/{current_time}/images")
    
    get_product_list(driver=driver, db_name=db_name, table_name=table_name, current_time=current_time, prefix=prefix)
    driver.quit()


