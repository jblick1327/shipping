"""
This module handles database interactions, including fetching and updating order data.
Provides options for mock database from CSV file.
"""

from dotenv import load_dotenv
import os
import csv
import pyodbc
import datetime
from utils import get_logger, load_config, get_full_path

logger = get_logger(__name__)

config = load_config()
DB_MODE = config["database"]["db_mode"]
CSV_FILE_PATH = get_full_path(config["database"]["csv_path"])
OUTPUT_DIR = get_full_path(config["paths"]["output_dir"])
TEMPLATE_PDF = get_full_path(config["paths"]["template_pdf"])

load_dotenv()

# Fetch ODBC credentials from environment variables (loaded via dotenv)
ODBC_DSN = os.getenv("ODBC_DSN")
ODBC_USER = os.getenv("ODBC_USER")
ODBC_PASSWORD = os.getenv("ODBC_PASSWORD")

if DB_MODE == "odbc":
    if not ODBC_DSN or not ODBC_USER or not ODBC_PASSWORD:
        logger.error("Missing ODBC credentials. Please check the .env file.")
        raise ValueError(
            "ODBC credentials are missing. Ensure ODBC_DSN, ODBC_USER, and ODBC_PASSWORD are set correctly."
        )


def fetch_order_data(order_number):
    """
    Fetches order data using the configured database mode (mock or ODBC).

    Args:
        order_number (str): The order number for which data is being retrieved.

    Returns:
        dict: Order data as a dictionary if found; None otherwise.
    """
    if DB_MODE == "mock":
        return mock_get_order_data(order_number)
    elif DB_MODE == "odbc":
        return get_odbc_order_data(order_number)
    else:
        logger.error(f"Invalid database mode: {DB_MODE}")
        return None


def mock_get_order_data(order_number):
    """
    Fetches order data from a mock CSV file in testing mode.

    Args:
        order_number (str): The order number for which data is being retrieved.

    Returns:
        dict: Order data as a dictionary if found; None otherwise.
    """
    try:
        with open(CSV_FILE_PATH, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if str(row["SSD_SHIPMENT_ID"]).strip() == str(order_number).strip():
                    logger.info(
                        f"Order data successfully fetched for Order Number: {order_number}"
                    )
                    return row
            logger.error(f"No data found for Order Number: {order_number}")
            return None
    except FileNotFoundError as e:
        logger.error(f"CSV file not found: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return None


def get_odbc_order_data(order_number):
    """
    Fetches order data from a database using an ODBC connection.

    Args:
        order_number (str): The order number for which data is being retrieved.

    Returns:
        dict: Order data as a dictionary if found; None otherwise.

    Raises:
        ValueError: If ODBC credentials are missing.
    """
    try:
        # Establish an ODBC connection using credentials from the environment
        connection = pyodbc.connect(
            f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}"
        )
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM OESSOD WHERE SSD_SHIPMENT_ID = ?", (order_number,)
        )
        row = cursor.fetchone()

        if row:
            # Extract column names and return data as a dictionary
            columns = [column[0] for column in cursor.description]
            logger.info(
                f"Order data successfully fetched for Order Number: {order_number}"
            )
            return dict(zip(columns, row))
        else:
            logger.error(f"No data found for Order Number: {order_number}")
            return None
    except pyodbc.Error as e:
        logger.error(f"Error querying database for Order Number {order_number}: {e}")
        return None
    finally:
        connection.close()


def update_shipping_data(
    order_number, tracking_number, carrier, weight, skid_cartons, quote_price
):
    """
    Updates shipping data for a given order based on the current database mode.

    Args:
        order_number (str): Order number for the update.
        tracking_number (str): Tracking number to be updated.
        carrier (str): Carrier name.
        weight (float): Weight of the shipment.
        skid_cartons (int): Total number of cartons in the shipment.
        quote_price (float): Quote price for the shipment.

    Returns:
        None
    """
    if DB_MODE == "mock":
        return mock_update_shipping_data(
            order_number, tracking_number, carrier, weight, skid_cartons, quote_price
        )
    elif DB_MODE == "odbc":
        return update_odbc_shipping_data(
            order_number, tracking_number, carrier, weight, skid_cartons, quote_price
        )
    else:
        logger.error(f"Invalid database mode: {DB_MODE}")


def mock_update_shipping_data(
    order_number, tracking_number, carrier, weight, skid_cartons, quote_price
):
    """
    Simulates updating shipping data in mock mode. Logs the input data without making actual changes.

    Args:
        order_number (str): Order number for the update.
        tracking_number (str): Tracking number to be updated.
        carrier (str): Carrier name.
        weight (float): Weight of the shipment.
        skid_cartons (int): Total number of cartons in the shipment.
        quote_price (float): Quote price for the shipment.

    Returns:
        None
    """
    logger.info("Mock Mode: Simulating database update.")
    logger.info(f"Order Number: {order_number} (Type: {type(order_number)})")
    logger.info(f"Tracking Number: {tracking_number} (Type: {type(tracking_number)})")
    logger.info(f"Carrier: {carrier} (Type: {type(carrier)})")
    logger.info(f"Weight: {weight} (Type: {type(weight)})")
    logger.info(f"Total Cartons: {skid_cartons} (Type: {type(skid_cartons)})")
    logger.info(f"Quote Price: {quote_price} (Type: {type(quote_price)})")
    logger.info("Simulated update completed.")


def update_odbc_shipping_data(
    order_number, tracking_number, carrier, weight, skid_cartons, quote_price
):
    """
    Updates shipping data in the database using an ODBC connection.

    Args:
        order_number (str): Order number for the update.
        tracking_number (str): Tracking number to be updated.
        carrier (str): Carrier name.
        weight (float): Weight of the shipment.
        skid_cartons (int): Total number of cartons in the shipment.
        quote_price (float): Quote price for the shipment.

    Returns:
        None

    Raises:
        pyodbc.Error: If an error occurs during the database query.
    """
    try:
        logger.info(
            f"Function called with parameters: Order Number: {order_number}, Tracking Number: {tracking_number}, Carrier: {carrier}, Weight: {weight}, Total Cartons: {skid_cartons}, Quote Price: {quote_price}"
        )

        connection = pyodbc.connect(
            f"DSN={ODBC_DSN};UID={ODBC_USER};PWD={ODBC_PASSWORD}"
        )
        cursor = connection.cursor()
        logger.info("ODBC connection established successfully.")

        logger.info(
            f"Checking for existence of Order Number: {order_number} in the database."
        )
        cursor.execute("SELECT ORDNO FROM OESHPU WHERE ORDNO = ?", (order_number,))
        record = cursor.fetchone()

        if record:
            logger.info(f"Order record found: {record}")

            if not tracking_number:
                logger.error(
                    f"Tracking number (COSTCENTER) is missing for Order Number: {order_number}. Update aborted."
                )
                return

            # Enforce constraints and ensure valid formats
            tracking_number = tracking_number[:30]
            carrier = carrier[:23]
            current_time = datetime.date.today().isoformat()
            weight = float(weight) if weight else 0.00
            skid_cartons = int(skid_cartons) if skid_cartons else 1
            quote_price = float(quote_price) if quote_price else 0.00

            update_query = """
                UPDATE OESHPU
                SET DATESHIP = ?, COSTCENTER = ?, SHIPVIA = ?, WEIGHTLBS = ?, PIECES = ?, FREIGHT = ?
                WHERE ORDNO = ?
            """
            logger.info(f"Executing update query for Order Number: {order_number}")
            logger.info(f"Query: {update_query}")
            logger.info(
                f"Parameters: {current_time}, {tracking_number}, {carrier}, {weight}, {skid_cartons}, {quote_price}, {order_number}"
            )

            cursor.execute(
                update_query,
                (
                    current_time,
                    tracking_number,
                    carrier,
                    weight,
                    skid_cartons,
                    quote_price,
                    order_number,
                ),
            )
            connection.commit()
            logger.info(
                f"Database successfully updated for Order Number: {order_number} with Tracking Number (COSTCENTER): {tracking_number}"
            )
        else:
            logger.error(
                f"No record found to update for Order Number: {order_number}. Update aborted."
            )
    except pyodbc.Error as e:
        logger.error(f"Database error while updating Order Number {order_number}: {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error occurred during update for Order Number {order_number}: {e}"
        )
    finally:
        try:
            logger.info("Closing ODBC connection...")
            connection.close()
            logger.info("ODBC connection closed successfully.")
        except Exception as e:
            logger.error(f"Error closing the ODBC connection: {e}")
