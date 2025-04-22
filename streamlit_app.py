import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import base64
from PIL import Image
import io
import threading
import requests
from pathlib import Path
import imghdr
import xlwt

from walmart import get_walmart_products
from aldi import get_aldi_products
from bjs import get_bjs_products
from costco import get_costco_products
from milams import get_milams_products
from publix import get_publix_products
from restaurant_depot import get_restaurant_depot_products
from sabor_tropical import get_sabor_tropical_products
from sams import get_sams_products
from target import get_target_products
from google_shopping_api import get_products as get_google_products

# Available stores
AVAILABLE_STORES = [
    "aldi",
    "bjs",
    "costco",
    "milams",
    "publix",
    "restaurant_depot",
    "sabor_tropical",
    "sams",
    "target",
    "walmart"
]

def create_database_table(db_name, table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

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

def get_products(store, db_name, table_name, current_time, prefix, item_count):
    if store == "aldi":
        get_aldi_products(db_name, table_name, store, current_time, prefix)
    elif store == "bjs":
        get_bjs_products(db_name, table_name, store, current_time, prefix)
    elif store == "costco":
        get_costco_products(db_name, table_name, store, current_time, prefix)
    elif store == "milams":
        get_milams_products(db_name, table_name, store, current_time, prefix)
    elif store == "publix":
        get_publix_products(db_name, table_name, store, current_time, prefix)
    elif store == "restaurant_depot":
        get_restaurant_depot_products(db_name, table_name, store, current_time, prefix)
    elif store == "sabor_tropical":
        get_sabor_tropical_products(db_name, table_name, store, current_time, prefix)
    elif store == "sams":
        get_sams_products(db_name, table_name, store, current_time, prefix)
    elif store == "target":
        get_target_products(db_name, table_name, store, current_time, prefix)
    elif store == "walmart":
        get_walmart_products_from_api(db_name, table_name, current_time, prefix, item_count)
    return "success"

def get_walmart_products_from_api(db_name, table_name, current_time, prefix, item_count, driver=None):
    if driver is None:
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options)
        should_quit_driver = True
    else:
        should_quit_driver = False
    
    try:
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
        
        driver.get(f"https://www.walmart.com/search?q={prefix}")
        time.sleep(2)
        elements = driver.find_elements(By.XPATH, '//*[@role="group"]')
        num = 0
        
        for element in elements:
            if num >= item_count:
                break

            image_url = ""
            title = ""
            rating = ""
            rating_count = ""
            product_link = ""
            price = ""
            download_url = ""
            store = "Walmart"

            driver.execute_script("arguments[0].scrollIntoView();", element)
            time.sleep(3)

            try:
                img_element = element.find_element(By.TAG_NAME, "img")
                image_url = img_element.get_dom_attribute("src")
                
                # Handle base64 images
                if image_url and image_url.startswith("data:image"):
                    try:
                        match = re.match(r"data:image/(\w+);base64,(.*)", image_url)
                        if match:
                            image_type, base64_data = match.groups()
                            image_type = image_type if image_type else "jpg"
                            download_url = f"products/{current_time}_{prefix}/images/{prefix}{section_id}.{image_type}"
                            
                            os.makedirs(os.path.dirname(download_url), exist_ok=True)
                            with open(download_url, 'wb') as file:
                                file.write(base64.b64decode(base64_data))
                    except Exception as e:
                        print(f"Error saving base64 image: {str(e)}")
                        download_url = ""
                # Handle regular URLs
                elif image_url and image_url.startswith("http"):
                    try:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            image_type = imghdr.what(None, response.content) or "jpg"
                            download_url = f"products/{current_time}_{prefix}/images/{prefix}{section_id}.{image_type}"
                            
                            os.makedirs(os.path.dirname(download_url), exist_ok=True)
                            with open(download_url, 'wb') as file:
                                file.write(response.content)
                    except Exception as e:
                        print(f"Error saving image URL: {str(e)}")
                        download_url = ""
            except:
                image_url = ""

            try:
                title_element = element.find_element(By.CLASS_NAME, "w_V_DM")
                title = title_element.text.strip()
            except:
                title = ""
            
            try:
                product_link_element = element.find_element(By.TAG_NAME, "a")
                product_link = product_link_element.get_dom_attribute("href")
            except:
                product_link = ""

            try:
                price_element = element.find_element(By.CLASS_NAME, "w_iUH7")
                price = price_element.text.strip()
            except:
                price = ""

            # Create database record
            db_record = (
                "https://walmart.com",
                "https://www.walmart.com" + product_link,
                "Walmart",
                store,
                title,
                price,
                download_url,  # Use the saved image path
                image_url,
                rating,
                rating_count,
                ""
            )

            # Create Excel record
            excel_record = [
                str(section_id),
                "https://walmart.com",
                "https://www.walmart.com" + product_link if product_link else "",
                "Walmart",
                store,
                "",
                title if title else "",
                "",
                price if price else "",
                download_url if download_url else "",  # Use the saved image path
                image_url if image_url else "",
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
            section_id += 1
            num += 1

        # Save Excel file
        excel_filename = f"products/{current_time}_{prefix}/walmart_products_{current_time}.xls"
        os.makedirs(os.path.dirname(excel_filename), exist_ok=True)
        workbook.save(excel_filename)
        st.success(f"Excel file saved as: {excel_filename}")

    except Exception as e:
        st.error(f"Error searching Walmart: {str(e)}")
    finally:
        if should_quit_driver:
            driver.quit()

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

def get_table_names(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    # Return table names in reverse order (newest first)
    return sorted([table[0] for table in tables], reverse=True)

def get_products_from_table(db_name, table_name, page=1, per_page=12):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # First check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        return None
        
    # Get total count of records
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_records = cursor.fetchone()[0]
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get paginated results
    cursor.execute(f"""
        SELECT * 
        FROM {table_name}
        WHERE price IS NOT NULL AND price != ''
        ORDER BY CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS FLOAT) ASC
        LIMIT {per_page} OFFSET {offset}
    """)
    products = cursor.fetchall()
    conn.close()
    return products, total_records

def compare_on_google(product_name, db_name, table_name, current_time):
    """Compare a product on Google Shopping"""
    with st.spinner("Searching Google Shopping..."):
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options)
        
        try:
            # Create a new table for Google comparison results
            create_database_table(db_name, table_name)
            get_google_products(driver, product_name, db_name, table_name, current_time, "google_", 5)
            
            # Display comparison results in card format
            st.subheader(f"Google Shopping Results for: {product_name}")
            products, total_records = get_products_from_table(db_name, table_name)
            if products:
                # Display products in a single column
                for product in products:
                    # Create a card-like container
                    st.markdown("---")  # Separator between cards
                    
                    # Display product image
                    image_path = product[7]  # image_file_name
                    image_url = product[8]   # image_link
                    
                    if not display_image(image_path, image_url):
                        st.warning("No image available")
                    
                    # Display product details
                    st.markdown(f"**{product[5]}**")  # product_name
                    st.markdown(f"**Price:** {product[6]}")  # price
                    st.markdown(f"**Store:** {product[4]}")  # store
                    
                    if product[9]:  # product_rating
                        st.markdown(f"**Rating:** {product[9]}")
                    if product[10]:  # product_review_number
                        st.markdown(f"**Reviews:** {product[10]}")
                    
                    # Add product page link
                    if product[2]:  # product_item_page_link
                        st.markdown(f"[Product Page]({product[2]})")
            else:
                st.warning("No comparison results found on Google Shopping.")
        except Exception as e:
            st.error(f"Error comparing on Google: {str(e)}")
        finally:
            driver.quit()

def compare_on_walmart(product_name, db_name, table_name, current_time):
    """Compare a product on Walmart"""
    with st.spinner("Searching Walmart..."):
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options)
        
        try:
            # Create a new table for Walmart comparison results
            create_database_table(db_name, table_name)
            get_walmart_products_from_api(db_name, table_name, current_time, product_name, 5, driver)
            
            # Display comparison results in card format
            st.subheader(f"Walmart Results for: {product_name}")
            products, total_records = get_products_from_table(db_name, table_name)
            if products:
                # Display products in a single column
                for product in products:
                    # Create a card-like container
                    st.markdown("---")  # Separator between cards
                    
                    # Display product image
                    image_path = product[7]  # image_file_name
                    image_url = product[8]   # image_link
                    
                    if not display_image(image_path, image_url):
                        st.warning("No image available")
                    
                    # Display product details
                    st.markdown(f"**{product[5]}**")  # product_name
                    st.markdown(f"**Price:** {product[6]}")  # price
                    st.markdown(f"**Store:** {product[4]}")  # store
                    
                    if product[9]:  # product_rating
                        st.markdown(f"**Rating:** {product[9]}")
                    if product[10]:  # product_review_number
                        st.markdown(f"**Reviews:** {product[10]}")
                    
                    # Add product page link
                    if product[2]:  # product_item_page_link
                        st.markdown(f"[Product Page]({product[2]})")
            else:
                st.warning("No comparison results found on Walmart.")
        except Exception as e:
            st.error(f"Error comparing on Walmart: {str(e)}")
        finally:
            driver.quit()

def display_image(image_path, image_url):
    """Display image from local path, URL, or base64 data"""
    try:
        # First try to load from local path
        if image_path and os.path.exists(image_path):
            image = Image.open(image_path)
            st.image(image, use_container_width=True)
            return True
        # If local path fails, try URL or base64
        elif image_url:
            if image_url == "Base64 image data":
                st.warning("Image is in base64 format and cannot be displayed directly")
                return False
            elif image_url.startswith('data:image'):
                # Handle base64 encoded image
                try:
                    # Extract the base64 data
                    base64_data = image_url.split(',')[1]
                    # Decode the base64 data
                    image_data = base64.b64decode(base64_data)
                    # Create an image from the decoded data
                    image = Image.open(io.BytesIO(image_data))
                    st.image(image, use_container_width=True)
                    return True
                except Exception as e:
                    st.error(f"Error decoding base64 image: {str(e)}")
                    return False
            else:
                # Handle regular URL
                response = requests.get(image_url)
                if response.status_code == 200:
                    image = Image.open(io.BytesIO(response.content))
                    st.image(image, use_container_width=True)
                    return True
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
    return False

def match_image_with_google_lens(image_path, current_time):
    """Match image using Google Lens"""
    try:
        # Set up Chrome WebDriver with undetected-chromedriver
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options)

        # Get absolute path of the image
        absolute_path = os.path.abspath(image_path)
        
        # Open Google Images
        driver.get("https://www.google.com/imghp")
        time.sleep(2)

        # Click the "Search by Image" button (Google Lens icon)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                lens_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Search by image']"))
                )
                lens_button.click()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)

        time.sleep(2)

        # Upload Image
        upload_tab = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='upload a file  ']"))
        )
        upload_tab.click()
        time.sleep(2)

        # Upload the file
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(absolute_path)
        time.sleep(5)  # Wait for results to load

        # Get image results with retries
        matched_images = []
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Wait for results to be visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "img"))
                )
                
                # Get all image elements
                results = driver.find_elements(By.TAG_NAME, "img")
                search_results = [result.get_attribute('src') for result in results]

                # Store valid image URLs
                for idx, img_url in enumerate(search_results):
                    if idx > 2:  # Skip first 3 results as they're usually UI elements
                        if img_url and (img_url.startswith("http") or img_url.startswith("data:image")):
                            matched_images.append(img_url)
                
                if matched_images:
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)

        driver.quit()
        return matched_images

    except Exception as e:
        st.error(f"Error matching image: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None

def save_selected_products(selected_products, db_name):
    """Save selected products to items_search table"""
    # Create items_search table if it doesn't exist
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS items_search (
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
        score TEXT,
        saved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    
    # Insert selected products
    insert_query = """
    INSERT INTO items_search (
        store_page_link, product_item_page_link, platform, store, 
        product_name, price, image_file_name, image_link, 
        product_rating, product_review_number, score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        for product in selected_products:
            # Extract the values we need from the product tuple
            # product[0] is id, which we skip as it's auto-generated in items_search
            record = (
                product[1],  # store_page_link
                product[2],  # product_item_page_link
                product[3],  # platform
                product[4],  # store
                product[5],  # product_name
                product[6],  # price
                product[7],  # image_file_name
                product[8],  # image_link
                product[9],  # product_rating
                product[10], # product_review_number
                product[11] if len(product) > 11 else ""  # score
            )
            cursor.execute(insert_query, record)
            conn.commit()
        return True
    except Exception as e:
        print(f"Error saving product: {str(e)}")
        return False
    finally:
        conn.close()

def display_product_card(product, db_name, is_saved_item=False):
    col1, col2 = st.columns([1, 3])
    
    # Create a unique key for the checkbox based on product details
    checkbox_key = f"select_{product[0]}_{product[4]}_{product[6]}"  # Using id, store, and price to create unique key
    
    with col1:
        # Display product image
        image_path = product[7]  # image_file_name
        image_url = product[8]   # image_link
        
        if not display_image(image_path, image_url):
            st.warning("No image available")
    
    with col2:
        # Add checkbox for selection
        if not is_saved_item:
            # Initialize selected_products as a list if it doesn't exist
            if 'selected_products' not in st.session_state:
                st.session_state.selected_products = []
            
            # Check if this product is already selected
            is_selected = st.checkbox("Select for saving", key=checkbox_key)
            
            # Update selected_products based on checkbox state
            if is_selected:
                if product not in st.session_state.selected_products:
                    st.session_state.selected_products.append(product)
                    st.rerun()  # Force a rerun to update the sidebar
            else:
                if product in st.session_state.selected_products:
                    st.session_state.selected_products.remove(product)
                    st.rerun()  # Force a rerun to update the sidebar
        
        # Display product details
        st.markdown(f"### {product[5]}")  # product_name
        
        # Display price - product[6] contains the price
        if product[5]:
            st.markdown(f"**Price:** ${product[5]}")
        else:
            st.markdown("**Price:** Not available")
            
        st.markdown(f"**Store:** {product[4]}")  # store
        
        if product[9]:  # product_rating
            st.markdown(f"**Rating:** {product[9]}")
        if product[10]:  # product_review_number
            st.markdown(f"**Reviews:** {product[10]}")
        
        # Add product page link
        if product[2]:  # product_item_page_link
            st.markdown(f"[Product Page]({product[2]})")
        
        # Add comparison buttons
        col3, col4, col5 = st.columns(3)
        with col3:
            if st.button("Compare on Google", key=f"google_{product[0]}"):
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                table_name = f"google_comparison_{current_time}"
                compare_on_google(product[5], db_name, table_name, current_time)
        with col4:
            if st.button("Compare on Walmart", key=f"walmart_{product[0]}"):
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                table_name = f"walmart_comparison_{current_time}"
                compare_on_walmart(product[5], db_name, table_name, current_time)
        with col5:
            match_button = st.button("Match Images", key=f"match_{product[0]}")
    
    st.markdown("---")  # Add a separator between products

def display_google_search_results(db_name, table_name):
    """Display Google search results in a dedicated section"""
    products = get_products_from_table(db_name, table_name)
    if products:
        st.subheader("Google Shopping Results")
        for product in products:
            display_product_card(product, db_name)
    else:
        st.warning("No Google search results found.")

def main():
    st.set_page_config(page_title="Product Search", layout="wide")
    st.title("Product Search Application")
    
    # Define database name at the start
    db_name = "product_data.db"
    
    # Create products directory if it doesn't exist
    Path("products").mkdir(exist_ok=True)
    
    # Initialize session state for pagination and selected products
    if 'page' not in st.session_state:
        st.session_state.page = 1
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = []
    
    # Sidebar
    with st.sidebar:
        # Always show the Selected Products section
        st.header("Selected Products")
        num_selected = len(st.session_state.selected_products)
        st.write(f"Number of selected products: {num_selected}")
        
        # Show save button if there are selected products
        if num_selected > 0:
            if st.button("Save Selected Products"):
                if save_selected_products(st.session_state.selected_products, db_name):
                    st.success("Selected products have been saved successfully!")
                    st.session_state.selected_products = []  # Clear selections after saving
                    st.rerun()  # Rerun to update the UI
                else:
                    st.error("Failed to save some products. Please try again.")
        
        # Display previous searches
        st.header("Previous Searches")
        table_names = get_table_names(db_name)
        if table_names:
            selected_table = st.selectbox("Select a previous search", table_names)
        
        # Search options
        st.header("Search Options")
        selected_store = st.selectbox("Select Store", AVAILABLE_STORES)
        search_button = st.button("Search")
    
    # Main content area
    if search_button:
        try:
            with st.spinner("Searching products..."):
                # Create a unique table name based on store and timestamp
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                table_name = f"{selected_store}_{current_time}"
                
                # Create table and get products
                create_database_table(db_name, table_name)
                get_products(selected_store, db_name, table_name, current_time, "", 0)
                
                # Display results with pagination
                products, total_records = get_products_from_table(db_name, table_name, st.session_state.page)
                if products:
                    st.header("Search Results")
                    
                    # Pagination controls
                    items_per_page = 12
                    total_pages = (total_records + items_per_page - 1) // items_per_page
                    
                    # Display current page number and total pages
                    st.write(f"Page {st.session_state.page} of {total_pages} (Total Records: {total_records})")
                    
                    # Pagination buttons
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.session_state.page > 1:
                            if st.button("Previous Page"):
                                st.session_state.page -= 1
                                st.rerun()
                    with col2:
                        st.write("")  # Empty column for spacing
                    with col3:
                        if st.session_state.page < total_pages:
                            if st.button("Next Page"):
                                st.session_state.page += 1
                                st.rerun()
                    
                    # Display products for current page
                    for product in products:
                        display_product_card(product, db_name)
                    
                    # Add download button
                    all_products, _ = get_products_from_table(db_name, table_name, 1, total_records)
                    df = pd.DataFrame(all_products, columns=[
                        "ID", "Store Page Link", "Product Page Link", "Platform", "Store",
                        "Product Name", "Price", "Image File", "Image Link", "Rating",
                        "Review Count", "Score"
                    ])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download results as CSV",
                        data=csv,
                        file_name=f"{selected_store}_products_{current_time}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No products found.")
        except Exception as e:
            st.error(f"Error during search: {str(e)}")
    
    # Display selected previous search with pagination
    if 'selected_table' in locals() and selected_table:
        try:
            products, total_records = get_products_from_table(db_name, selected_table, st.session_state.page)
            if products:
                st.header(f"Previous Search: {selected_table}")
                
                # Pagination controls for previous search
                items_per_page = 12
                total_pages = (total_records + items_per_page - 1) // items_per_page
                
                # Display current page number and total pages
                st.write(f"Page {st.session_state.page} of {total_pages} (Total Records: {total_records})")
                
                # Pagination buttons
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if st.session_state.page > 1:
                        if st.button("Previous Page", key="prev_prev"):
                            st.session_state.page -= 1
                            st.rerun()
                with col2:
                    st.write("")  # Empty column for spacing
                with col3:
                    if st.session_state.page < total_pages:
                        if st.button("Next Page", key="next_prev"):
                            st.session_state.page += 1
                            st.rerun()
                
                # Display products for current page
                for product in products:
                    display_product_card(product, db_name)
        except Exception as e:
            st.error(f"Error loading previous search: {str(e)}")

if __name__ == "__main__":
    main() 