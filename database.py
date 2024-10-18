from dotenv import load_dotenv
import os
import csv
import pyodbc
import configparser
import datetime
from utils import log_error, log_info

# Step 1: Load the .env file (for ODBC credentials)
load_dotenv()  # This will load the .env file from the current directory

# Step 2: Load the config.ini file (for general settings)
config = configparser.ConfigParser()
config.read('config.ini')

# Step 3: Fetch general settings from config.ini
DB_MODE = config['database']['db_mode']
CSV_FILE_PATH = config['database'].get('csv_path', 'data/OESSOD_500_most_recent.csv')
TEMPLATE_PDF = config['paths']['template_pdf']
OUTPUT_DIR = config['paths']['output_dir']

# Step 4: Fetch ODBC credentials from environment variables loaded by .env
ODBC_DSN = os.getenv('ODBC_DSN')
ODBC_USER = os.getenv('ODBC_USER')
ODBC_PASSWORD = os.getenv('ODBC_PASSWORD')

# Check if ODBC credentials are missing when using ODBC mode
if DB_MODE == 'odbc':
    if not ODBC_DSN or not ODBC_USER or not ODBC_PASSWORD:
        log_error("Missing ODBC credentials. Please check the .env file.")
        raise ValueError("Missing ODBC credentials. Ensure ODBC_DSN, ODBC_USER, and ODBC_PASSWORD are set.")


# Fetch order data based on the database mode
def fetch_order_data(order_number):
    if DB_MODE == 'mock':
        return mock_get_order_data(order_number)
    elif DB_MODE == 'odbc':
        return get_odbc_order_data(order_number)
    else:
        log_error(f"Invalid database mode specified: {DB_MODE}")
        return None

# Mock function to fetch data from CSV
def mock_get_order_data(order_number):
    try:
        with open(CSV_FILE_PATH, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if str(row['SSD_SHIPMENT_ID']).strip() == str(order_number).strip():  # Ensure matching format
                    log_info(f"Order data successfully fetched for Order Number: {order_number}")
                    return row
            log_error(f"No data found for Order Number: {order_number}")
            return None
    except FileNotFoundError as e:
        log_error(f"CSV file not found: {e}")
        return None
    except Exception as e:
        log_error(f"Error reading CSV file: {e}")
        return None

# Fetch order data using ODBC
def get_odbc_order_data(order_number):
    try:
        connection = pyodbc.connect(f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}")
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM OESSOD WHERE SSD_SHIPMENT_ID = ?", (order_number,))
        row = cursor.fetchone()
        if row:
            columns = [column[0] for column in cursor.description]
            log_info(f"Order data successfully fetched for Order Number: {order_number}")
            return dict(zip(columns, row))
        else:
            log_error(f"No data found for Order Number: {order_number}")
            return None
    except pyodbc.Error as e:
        log_error(f"Error querying database for Order Number {order_number}: {e}")
        return None
    finally:
        connection.close()

# Function to update shipping data (ODBC or mock depending on the mode)
def update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    if DB_MODE == 'mock':
        return mock_update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price)
    elif DB_MODE == 'odbc':
        return update_odbc_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price)
    else:
        log_error(f"Invalid database mode specified: {DB_MODE}")

# Mock update function for CSV (testing mode)
def mock_update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    log_info(f"Simulating update of Order Number: {order_number} in the CSV.")
    log_info(f"Order Number: {order_number}, Carrier: {carrier}, Weight: {weight}, Cartons: {total_cartons}, Quote Price: {quote_price}")
    # This is a simulation; no actual update to the CSV file

# Update function for ODBC (production mode)
def update_odbc_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    try:
        connection = pyodbc.connect(f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}")
        cursor = connection.cursor()
        cursor.execute("SELECT ORDNO FROM OESHPU WHERE ORDNO = ?", (order_number,))
        record = cursor.fetchone()

        if record:
            current_time = datetime.datetime.now().date().isoformat()
            update_query = """
                UPDATE OESHPU
                SET DATESHIP = ?, COSTCENTER = ?, SHIPVIA = ?, WEIGHTLBS = ?, PIECES = ?, FREIGHT = ?
                WHERE ORDNO = ?
            """
            cursor.execute(update_query, (current_time, tracking_number, carrier, weight, total_cartons, quote_price, order_number))
            connection.commit()
            log_info(f"Database successfully updated for Order Number: {order_number}")
        else:
            log_error(f"No record found to update for Order Number: {order_number}")
    except pyodbc.Error as e:
        log_error(f"Error updating record for Order Number {order_number}: {e}")
    finally:
        connection.close()
