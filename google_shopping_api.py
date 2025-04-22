import requests
from datetime import datetime, timedelta
import imghdr
import sqlite3
import os

from selenium.webdriver.common.by import By
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import base64
from flask_cors import CORS

def create_database_table(db_name, table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(table_name)

    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY,
        store_page_link TEXT,
        product_item_page_link TEXT,
        platform TEXT,
        store TEXT,
        product_name TEXT,
        price TEXT,
        image_file_name TEXT,
        image_link TEXT,
        product_rating TEXT,
        product_review_number TEXT,
        score TEXT
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

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

def clean_price(value):
    """Convert price from string to float."""
    if not value or value.strip() == "":
        return 0.0  # Default to 0 if missing

    try:
        # Remove currency symbols, commas, and whitespace
        cleaned = value.strip().replace("$", "").replace(",", "").replace(" ", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0  # Return 0 if conversion fails

def clean_rating(value):
    """Convert rating from string to float, handling empty values."""
    if not value or value.strip() == "":  
        return 0.0  # Default to 0 if empty or None

    try:
        return float(value)  # Convert regular number
    except ValueError:
        return 0.0  # Return 0 if conversion fails

def get_products(driver, keyword, db_name, table_name, current_time, prefix, item_count):
    section_id = 1
    products = []
    
    driver.get(f"https://www.google.com/search?q={keyword}+price&tbm=shop")
    time.sleep(2)
    elements = driver.find_elements(By.CLASS_NAME, "Ez5pwe")
    num = 0
    
    for element in elements:
        if(num >= item_count):
            break

        image_url = ""
        title = ""
        rating = ""
        rating_count = ""
        product_link = ""
        price = ""
        download_url = ""
        store = ""

        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.find_element(By.CLASS_NAME, "MtXiu").click()
        time.sleep(3)

        try:
            img_element = element.find_element(By.CLASS_NAME, "VeBrne")
            image_url = img_element.get_dom_attribute("src")
        except:
            image_url = ""
        
        if(image_url):
            try:
                if image_url.startswith("http"):  # If it's a URL
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        image_type = imghdr.what(None, response.content) or "jpg"  # Default to jpg if unknown
                        download_url = f"products/{current_time}_{keyword}/images/{prefix}{section_id}.{image_type}"
                        
                        os.makedirs(os.path.dirname(download_url), exist_ok=True)
                        with open(download_url, 'wb') as file:
                            file.write(response.content)

                elif image_url.startswith("data:image"):  # If it's a base64 string
                    match = re.match(r"data:image/(\w+);base64,(.*)", image_url)
                    if match:
                        image_type, base64_data = match.groups()
                        image_type = image_type if image_type else "jpg"  # Default type
                        
                        download_url = f"products/{current_time}_{keyword}/images/{prefix}{section_id}.{image_type}"
                        
                        os.makedirs(os.path.dirname(download_url), exist_ok=True)
                        with open(download_url, 'wb') as file:
                            file.write(base64.b64decode(base64_data))
                        image_url = "Raw image"

            except Exception as e:
                print("Error saving image:", e)
        try:
            title_element = element.find_element(By.CLASS_NAME, "gkQHve")
            title = title_element.text.strip()
        except:
            title = ""
        
        try:
            product_link_element = driver.find_element(By.CLASS_NAME, "P9159d")
            product_link = product_link_element.get_dom_attribute("href")
        except:
            product_link = ""

        try:
            store_element = element.find_element(By.CLASS_NAME, "Z9qvte")
            store = store_element.text.strip()
        except:
            store = ""

        try:
            price_element = element.find_element(By.CLASS_NAME, "lmQWe")
            price = price_element.text.strip()
        except:
            price = ""

        try:
            rating_element = element.find_element(By.CLASS_NAME, "yi40Hd")
            rating = rating_element.text.strip()
        except:
            rating = ""

        try:
            rating_count_element = element.find_element(By.CLASS_NAME, "RDApEe")
            rating_count = rating_count_element.text.strip()
            rating_count = clean_rating_count(rating_count)
        except:
            rating_count = 0

        price_float = clean_price(price)
        score = (clean_rating(rating) * 2) + (rating_count / 100) - (price_float / 10)

        # Create record with correct field order matching the database schema
        db_record = (
            "https://google.com",  # store_page_link
            product_link,          # product_item_page_link
            "Google",             # platform
            store,                # store
            title,                # product_name
            price,                # price
            download_url,         # image_file_name
            image_url,            # image_link
            str(rating),          # product_rating
            str(rating_count),    # product_review_number
            str(score)            # score
        )

        insert_product_record(db_name, table_name, db_record)
        products.append(db_record)  # Use the same record structure as the database
        section_id = section_id + 1
        num = num + 1

    driver.quit()
    return products

def clean_rating_count(value):
    """Convert rating count from string to an integer."""
    if not value or value.strip() == "":  
        return 0  # Default to 0 if empty or None

    value = value.strip("()")  # Remove parentheses

    if 'K' in value:
        return int(float(value.replace('K', '')) * 1000)  # Convert '5.1K' to 5100

    try:
        return int(value)  # Convert regular number
    except ValueError:
        return 0  # Return 0 if conversion fails