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
    "https://www.instacart.com/store/publix/collections/n-bogo-deals-76652",
    "https://www.instacart.com/store/publix/collections/produce",
    "https://www.instacart.com/store/publix/collections/meat-and-seafood",
    "https://www.instacart.com/store/publix/collections/dairy",
    "https://www.instacart.com/store/publix/collections/snacks-and-candy",
    "https://www.instacart.com/store/publix/collections/3095-prepared-foods",
    "https://www.instacart.com/store/publix/collections/baked-goods",
    "https://www.instacart.com/store/publix/collections/frozen",
    "https://www.instacart.com/store/publix/collections/household",
    "https://www.instacart.com/store/publix/collections/canned-goods",
    "https://www.instacart.com/store/publix/collections/personal-care",
    "https://www.instacart.com/store/publix/collections/breakfast-foods",
    "https://www.instacart.com/store/publix/collections/floral",
    "https://www.instacart.com/store/publix/collections/pets",
    "https://www.instacart.com/store/publix/collections/condiments-sauces",
    "https://www.instacart.com/store/publix/collections/dry-goods-pasta",
    "https://www.instacart.com/store/publix/collections/3089-deli",
    "https://www.instacart.com/store/publix/collections/beverages",
    "https://www.instacart.com/store/publix/collections/health-care",
    "https://www.instacart.com/store/publix/collections/baking-essentials",
    "https://www.instacart.com/store/publix/collections/oils-vinegars-spices",
    "https://www.instacart.com/store/publix/collections/kitchen-supplies",
    "https://www.instacart.com/store/publix/collections/3670-catering",
    "https://www.instacart.com/store/publix/collections/857-miscellaneous-grocery",
    "https://www.instacart.com/store/publix/collections/party-gifts",
    "https://www.instacart.com/store/publix/collections/office-craft",
    "https://www.instacart.com/store/publix/collections/baby",
    "https://www.instacart.com/store/publix/collections/dynamic_collection-sales",
    "https://www.instacart.com/store/publix/collections/n-new-and-interesting-31303",
    "https://www.instacart.com/store/publix/collections/n-decadent-dessert-cakes-74191",
    "https://www.instacart.com/store/publix/collections/n-deli-meals-and-sides-34931",
    "https://www.instacart.com/store/publix/collections/rc-fresh-cut-fruit",
    "https://www.instacart.com/store/publix/collections/n-platters-76692",
    "https://www.instacart.com/store/publix/collections/n-quick-snacks-and-candy-69202",
    "https://www.instacart.com/store/publix/collections/n-ready-to-cook-82412",
    "https://www.instacart.com/store/publix/collections/n-subs-and-wraps-94533",
    "https://www.instacart.com/store/publix/collections/n-tailgating-11955",
    "https://www.instacart.com/store/publix/collections/n-2025-02-italian-savings-event-53147"
]

category_titles = [
    "BOGO",
    "Produce",
    "Meat & Seafood",
    "Dairy & Eggs",
    "Snacks & Candy",
    "Prepared Foods",
    "Bakery",
    "Frozen",
    "Household",
    "Canned Goods & Soups",
    "Personal Care",
    "Breakfast",
    "Floral",
    "Pets",
    "Condiments & Sauces",
    "Dry Goods & Pasta",
    "Deli",
    "Beverages",
    "Health Care",
    "Baking Essentials",
    "Oils, Vinegars, & Spices",
    "Kitchen Supplies",
    "Catering",
    "Miscellaneous",
    "Party & Gift Supplies",
    "Office & Craft",
    "Baby",
    "Sales",
    "New and Interesting",
    "Decadent Dessert Cakes",
    "Deli Meals and Sides",
    "Fresh Cut Fruit",
    "Platters",
    "Quick Snacks and Candy",
    "Ready to Cook",
    "Subs and Wraps",
    "Tailgating",
    "Italian Savings Event"
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

            db_record = (
                "https://instacart.com",
                product_link,
                "Instacart",
                "Publix",
                title,
                price,
                download_url,
                image_url,
                rating,
                rating_count,
                ""
            )

            insert_product_record(db_name, table_name, db_record)
            
            products.append(record)
            print(record)
            section_id = section_id + 1
        num = num + 1
    # driver.quit()
    return products

def get_publix_products(db_name, table_name, store, current_time, prefix):
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


