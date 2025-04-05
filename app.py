import requests
import xlwt
from datetime import datetime, timedelta
import os
import imghdr
import sqlite3

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

from flask import Flask, render_template, send_from_directory, request, jsonify
import base64
from flask_cors import CORS

from walmart import get_records

app = Flask(__name__)
CORS(app)

# Remove timeout limit
app.config['TIMEOUT'] = None
app.config['PERMANENT_SESSION_LIFETIME'] = None

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

def get_products(store, db_name, table_name, current_time, prefix, item_count):
    get_records(db_name, table_name, store, current_time, prefix)
    return "success"

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

def sanitize_table_name(name):
    # Replace any non-alphanumeric characters (except underscores) with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure the name starts with a letter
    if not sanitized[0].isalpha():
        sanitized = 'table_' + sanitized
    return sanitized

@app.route('/')
def index():
    db_name = "product_data.db"
    page = request.args.get('page', 1, type=int)
    
    # Function to fetch table names
    def get_table_names(db_name):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]

    # Fetch the table names
    table_names = get_table_names(db_name)

    # Pass the table names to the template
    return render_template('index.html', table_names=table_names, page=page, total_pages=0)

@app.route('/products/<table_name>')
def get_products_by_table(table_name):
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Number of products per page
        db_name = "product_data.db"

        def get_table_names(db_name):
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            return [table[0] for table in tables]
        
        # Function to fetch product data from a specific table with pagination
        def get_products_from_table(db_name, table_name, page, per_page):
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            
            # First check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                conn.close()
                return None
                
            offset = (page - 1) * per_page  # Calculate the offset for pagination
            
            cursor.execute(f"""
                SELECT * 
                FROM {table_name}
                WHERE price IS NOT NULL AND price != ''
                ORDER BY CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS FLOAT) ASC
                LIMIT {per_page} OFFSET {offset}
            """)
            products = cursor.fetchall()
            conn.close()
            return products

        # Fetch the products for the selected table
        products = get_products_from_table(db_name, table_name, page, per_page)
        
        if products is None:
            # Table doesn't exist
            return render_template(
                'index.html', 
                table_names=get_table_names(db_name), 
                error=f"Table '{table_name}' not found",
                page=1,
                total_pages=0
            )
        
        # Fetch total number of products to calculate total pages
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE price IS NOT NULL AND price != ''")
        total_products = cursor.fetchone()[0]
        conn.close()

        total_pages = (total_products // per_page) + (1 if total_products % per_page != 0 else 0)

        # Return the template with the products and pagination info
        return render_template(
            'index.html', 
            table_names=get_table_names(db_name), 
            products=products, 
            selected_table=table_name,
            page=page,
            total_pages=total_pages
        )
    except Exception as e:
        print(f"Error in get_products_by_table: {str(e)}")
        return render_template(
            'index.html', 
            table_names=get_table_names(db_name), 
            error=f"Error retrieving products: {str(e)}",
            page=1,
            total_pages=0
        )

@app.route('/products/<path:filename>')
def serve_products(filename):
    return send_from_directory('products', filename)

@app.route('/submit_products', methods=['POST'])
def submit_products():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400
            
        selected_products = data.get('products', [])
        if not selected_products:
            return jsonify({"message": "No products selected."}), 400

        # Database connection
        db_name = "product_data.db"
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Ensure the items_search table exists
        create_database_table(db_name, "items_search")

        insert_query = """
        INSERT INTO items_search (store_page_link, product_item_page_link, platform, store, product_name, price, image_file_name, image_link, product_rating, product_review_number, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Insert each product (excluding 'id')
        for product in selected_products:
            product_data = tuple(product[1:])  # Exclude the first element (id)
            cursor.execute(insert_query, product_data)

        conn.commit()
        conn.close()

        return jsonify({"message": "Products successfully inserted into items_search.", "products": selected_products}), 200

    except Exception as e:
        print(f"Error in submit_products: {str(e)}")
        return jsonify({"message": f"Error submitting data: {str(e)}"}), 500

@app.route('/get_products', methods=['GET'])
def get_products_api():
    try:
        store = request.args.get("store", "").strip()
        item_count = int(request.args.get("item_count", "").strip())

        if not store:
            return jsonify({"error": "Store parameter is required"}), 400

        titleData = ["id","Store page link", "Product item page link", "Platform", "Store", "Product_description", "Product Name", "Units/Counts", "Price", "image_file_names", "Image_Link", "Store Rating", "Store Review number", "Product Rating", "Product Review number"]
        widths = [10,50,50,60,45,70,35,25,20,130,130,30,30,30,30,60]
        style = xlwt.easyxf('font: bold 1; align: horiz center')
        
        if(not os.path.isdir("products")):
            os.mkdir("products")

        now = datetime.now()
        current_time = now.strftime("%m_%d_%Y_%H_%M_%S")
        prefix = now.strftime("%Y%m%d%H%M%S%f_")

        db_name = "product_data.db"
        table_name = sanitize_table_name(f"search_{current_time}_{store}")
        
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Sheet1')
        
        for col_index, value in enumerate(titleData):
            first_col = sheet.col(col_index)
            first_col.width = 256 * widths[col_index]  # 20 characters wide
            sheet.write(0, col_index, value, style)
        
        create_database_table(db_name, table_name)
        result = get_products(store=store, db_name=db_name, table_name=table_name, current_time=current_time, prefix=prefix, item_count=item_count)
        
        if result != "success":
            return jsonify({"error": "Failed to fetch products"}), 500

        return jsonify({"message": "Products fetched successfully", "table_name": table_name})

    except Exception as e:
        print(f"Error in get_products_api: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    db_name = "product_data.db"
    create_database_table(db_name, "items_search")
    app.run(
        host="0.0.0.0", 
        port=5000,
        threaded=True
    )



