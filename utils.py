import logging
import os
from datetime import datetime 
import re
from PIL import ImageFont

# Define the current date in the format YYYY-MM-DD
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# Logging setup
def log_info(message):
    """Log an info message."""
    logging.info(message)

def log_error(message):
    """Log an error message."""
    logging.error(message)

# Function to convert relative paths to absolute paths
def get_full_path(relative_path):
    """
    Convert a relative path into an absolute path.
    """
    return os.path.abspath(os.path.join(os.getcwd(), relative_path))

# Function to ensure the output directory exists
def ensure_directory_exists(output_folder):
    """
    Ensure that the output directory exists. If it doesn't, create it.
    """
    os.makedirs(output_folder, exist_ok=True)
    log_info(f"Ensured that output directory exists: {output_folder}")

def ensure_directory_exists_with_date(output_dir):
    """
    Ensure the output directory exists with a folder structure based on the current date.
    The folder structure should be: output_dir/'Month YYYY'/'Month DD' (e.g., 'October 2024/October 26').
    """
    # Get the current date details
    current_date = datetime.now()
    year = current_date.strftime("%Y")  # Year as a 4-digit string
    month_name = current_date.strftime("%B")  # Full month name (e.g., "October")
    day = current_date.strftime("%d")  # Day as a 2-digit string
    
    # Create outer folder as "Month YYYY" (e.g., "October 2024")
    outer_folder = f"{month_name} {year}"
    
    # Create inner folder as "Month DD" (e.g., "October 26")
    inner_folder = f"{month_name} {day}"
    
    # Construct the full folder path
    output_dir_with_date = os.path.join(output_dir, outer_folder, inner_folder)
    
    # Ensure that this folder structure exists
    os.makedirs(output_dir_with_date, exist_ok=True)

    return output_dir_with_date

def center_text_x(page, text, fontsize, part=1, total_parts=1):
    """
    Calculate the x-coordinate for centering text horizontally on the page.
    
    Args:
        page (fitz.Page): The PDF page object (not used directly here).
        text (str): The text to center.
        fontsize (int): The font size of the text.
        part (int): The current part of the page (if divided into multiple parts).
        total_parts (int): The total number of parts the page is divided into.
        
    Returns:
        float: The x-coordinate to center the text.
    """
    lines = text.split("\n")  # Split the text into individual lines
    widest_line_width = 0
    font = ImageFont.truetype("arial.ttf", fontsize)
    
    # Find the widest line in the multi-line text
    for line in lines:
        text_bbox = font.getbbox(line)
        text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width for each line
        if text_width > widest_line_width:
            widest_line_width = text_width

    # Calculate the available width for each part
    page_width = page.rect.width
    part_width = page_width / total_parts

    # Calculate the x position to center the widest line within its part
    x_position = ((part_width - widest_line_width) / 2) + (part - 1) * part_width

    return x_position

def adjust_font_size(page, text, max_text_width, max_font_size):
    """
    Adjust the font size of the text to fit within the specified width.
    
    Args:
        page (fitz.Page): The PDF page object (not used directly here).
        text (str): The text to fit.
        max_text_width (int): The maximum allowed width for the text.
        max_font_size (int): The maximum font size.
        
    Returns:
        int: The adjusted font size.
    """
    font_size = max_font_size
    font = ImageFont.truetype("arial.ttf", font_size)
    
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2] - text_bbox[0]  # Calculate text width

    # Reduce font size until the text fits within max_text_width
    while text_width > max_text_width and font_size > 10:
        font_size -= 1
        font = ImageFont.truetype("arial.ttf", font_size)
        text_bbox = font.getbbox(text)
        text_width = text_bbox[2] - text_bbox[0]

    return font_size

def validate_alphanumeric(value, field_name):
    """
    Validate if the field is alphanumeric.
    
    Args:
        value (str): The string to validate.
        field_name (str): The name of the field being validated.
        
    Returns:
        bool: True if valid, otherwise False.
    """
    if re.match(r'^[a-zA-Z0-9]+$', value.strip()):
        return True
    else:
        return False


def validate_numeric_field(value, allow_decimal=True):
    """
    Validate if the field is numeric, with an optional decimal.
    
    Args:
        value (str): The string to validate.
        allow_decimal (bool): If True, allows decimals. Defaults to True.
        
    Returns:
        bool: True if valid, otherwise False.
    """
    try:
        if allow_decimal:
            float(value.strip())  # Allow decimals
        else:
            int(value.strip())  # Only allow integers
        return True
    except ValueError:
        return False

def validate_order_number(order_number):
    """
    Validate if the order number contains only digits and optional periods.
    
    Args:
        order_number (str): The order number to be validated.
        
    Returns:
        bool: True if valid, otherwise False.
    """
    # Regular expression to allow only digits with an optional period and up to two decimal places
    return bool(re.match(r'^\d+(\.\d{1,2})?$', order_number.strip()))



