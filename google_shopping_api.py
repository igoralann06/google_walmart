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
import xlwt
import streamlit as st

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
    
    # Create Excel workbook
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Sheet1')
    
    # Define column headers and widths
    titleData = ["id", "Store page link", "Product item page link", "Platform", "Store", 
                "Product_description", "Product Name", "Units/Counts", "Price", 
                "image_file_names", "Image_Link", "Store Rating", "Store Review number", 
                "Product Rating", "Product Review number"]
    widths = [10, 50, 50, 60, 45, 70, 35, 25, 20, 130, 130, 30, 30, 30, 30, 60]
    style = xlwt.easyxf('font: bold 1; align: horiz center')
    
    # Write headers to Excel
    for col_index, value in enumerate(titleData):
        first_col = sheet.col(col_index)
        first_col.width = 256 * widths[col_index]
        sheet.write(0, col_index, value, style)
    
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
            # Skip base64 images
            if image_url and image_url.startswith("data:image"):
                image_url = "Base64 image data"
        except:
            image_url = ""

        try:
            title_element = element.find_element(By.CLASS_NAME, "tAxDx")
            title = title_element.text.strip()
        except:
            title = ""

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

        # Create database record
        db_record = (
            "https://google.com",
            product_link,
            "Google",
            store,
            title,
            price,
            download_url,
            image_url,
            rating,
            rating_count,
            score
        )

        # Create Excel record with safe string handling
        excel_record = [
            str(section_id),
            "https://google.com",
            product_link if product_link else "",
            "Google",
            store if store else "",
            "",
            title if title else "",
            "",
            price if price else "",
            download_url if download_url else "",
            "Base64 image data" if image_url and image_url.startswith("data:image") else (image_url if image_url else ""),
            "",
            "",
            rating if rating else "",
            str(rating_count) if rating_count else "0"
        ]

        # Write to Excel with safe string handling
        try:
            for col_index, value in enumerate(excel_record):
                if value is None:
                    value = ""
                # Ensure the value is a string and doesn't exceed Excel's limit
                safe_value = str(value)[:32767] if value else ""
                sheet.write(section_id, col_index, safe_value)
        except Exception as e:
            print(f"Error writing to Excel: {str(e)}")
            continue

        insert_product_record(db_name, table_name, db_record)
        products.append(db_record)
        section_id = section_id + 1
        num = num + 1

    # Save Excel file
    excel_filename = f"products/{current_time}_{prefix}/google_products_{current_time}.xls"
    os.makedirs(os.path.dirname(excel_filename), exist_ok=True)
    workbook.save(excel_filename)
    st.success(f"Excel file saved as: {excel_filename}")

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