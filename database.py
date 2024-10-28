from dotenv import load_dotenv
import os
import csv
import pyodbc
import configparser
import datetime
from utils import log_error, log_info

# Load environment variables from .env file, typically used for ODBC credentials
load_dotenv()

# Load settings from config.ini for database mode, file paths, etc.
config = configparser.ConfigParser()
config.read('config.ini')

# Fetch general settings from the config file
DB_MODE = config['database']['db_mode']  # Specifies the database mode (e.g., 'odbc' or 'mock')
CSV_FILE_PATH = config['database'].get('csv_path', 'data/OESSOD_500_most_recent.csv')  # Path to the CSV file for mock mode
TEMPLATE_PDF = config['paths']['template_pdf']
OUTPUT_DIR = config['paths']['output_dir']

# Fetch ODBC credentials from environment variables (loaded via dotenv)
ODBC_DSN = os.getenv('ODBC_DSN')
ODBC_USER = os.getenv('ODBC_USER')
ODBC_PASSWORD = os.getenv('ODBC_PASSWORD')

# Ensure ODBC credentials are set if operating in ODBC mode
if DB_MODE == 'odbc':
    if not ODBC_DSN or not ODBC_USER or not ODBC_PASSWORD:
        log_error("Missing ODBC credentials. Please check the .env file.")
        raise ValueError("ODBC credentials are missing. Ensure ODBC_DSN, ODBC_USER, and ODBC_PASSWORD are set correctly.")

# Fetch order data based on the configured database mode (either 'mock' or 'odbc')
def fetch_order_data(order_number):
    """Fetch order data using the appropriate database mode (mock or ODBC)."""
    if DB_MODE == 'mock':
        return mock_get_order_data(order_number)
    elif DB_MODE == 'odbc':
        return get_odbc_order_data(order_number)
    else:
        log_error(f"Invalid database mode: {DB_MODE}")
        return None

# Fetch order data from a mock CSV file (used in testing mode)
def mock_get_order_data(order_number):
    """Fetch order data from a CSV file in mock mode."""
    try:
        with open(CSV_FILE_PATH, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if str(row['SSD_SHIPMENT_ID']).strip() == str(order_number).strip():
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

# Fetch order data using ODBC (production mode)
def get_odbc_order_data(order_number):
    """Fetch order data from a database using ODBC."""
    try:
        # Establish an ODBC connection using credentials from the environment
        connection = pyodbc.connect(f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}")
        cursor = connection.cursor()
        # Execute query to fetch the order data
        cursor.execute("SELECT * FROM OESSOD WHERE SSD_SHIPMENT_ID = ?", (order_number,))
        row = cursor.fetchone()

        if row:
            # Extract column names and return data as a dictionary
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

def update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    """Update shipping data for the given order based on the current database mode."""
    if DB_MODE == 'mock':
        return mock_update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price)
    elif DB_MODE == 'odbc':
        return update_odbc_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price)
    else:
        log_error(f"Invalid database mode: {DB_MODE}")


# Simulate updating shipping data in mock mode (no actual changes made)
def mock_update_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    """Simulate updating shipping data in mock mode (testing)."""
    log_info(f"Simulating update of Order Number: {order_number} in the CSV.")
    log_info(f"Order Number: {order_number}, Carrier: {carrier}, Weight: {weight}, Cartons: {total_cartons}, Quote Price: {quote_price}")
    # This is a mock update; no actual changes to the CSV

def update_odbc_shipping_data(order_number, tracking_number, carrier, weight, total_cartons, quote_price):
    """Update shipping data in the ODBC database."""
    try:
        # Establish ODBC connection using credentials from environment
        connection = pyodbc.connect(f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}")
        cursor = connection.cursor()

        # Check if the order exists in the database
        cursor.execute("SELECT ORDNO FROM OESHPU WHERE ORDNO = ?", (order_number,))
        record = cursor.fetchone()

        if record:
            # Prepare and execute the update query
            current_time = datetime.datetime.now().strftime('%Y-%m-%d')  # Ensure correct date format
            weight = float(weight) if weight else 0.00  # Ensure numeric format with two decimal places
            total_cartons = float(total_cartons) if total_cartons else 0.00  # Ensure numeric format with two decimal places
            quote_price = float(quote_price) if quote_price else 0.00  # Ensure numeric format with two decimal places
            
            update_query = """
                UPDATE OESHPU
                SET DATESHIP = ?, COSTCENTER = ?, SHIPVIA = ?, WEIGHTLBS = ?, PIECES = ?, FREIGHT = ?
                WHERE ORDNO = ?
            """
            cursor.execute(update_query, (current_time, tracking_number, carrier, weight, total_cartons, quote_price, order_number))
            connection.commit()  # Commit the transaction
            log_info(f"Database successfully updated for Order Number: {order_number}")
        else:
            log_error(f"No record found to update for Order Number: {order_number}")
    except pyodbc.Error as e:
        log_error(f"Error updating record for Order Number {order_number}: {e}")
    finally:
        connection.close()  # Ensure the connection is always closed


