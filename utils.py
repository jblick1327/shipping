import logging
import sys
import os
import configparser
from datetime import datetime
import re
from PIL import ImageFont


#Logging & Configuration
def get_logger(name: str = __name__) -> logging.Logger:
    """
    Returns a configured logger. All modules should import and use this.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def load_config(config_path="config.ini"):
    """
    Resolves a relative path to an absolute path based on the script's directory.

    Args:
        relative_path (str): Relative path to resolve.

    Returns:
        str: Absolute path.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to config.ini
    full_config_path = os.path.join(base_dir, config_path)
    # Load the configuration
    config = configparser.ConfigParser()
    config.read(full_config_path)
    return config


CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


#File & Path Helpers
def get_full_path(relative_path):
    """
    Resolves a relative path to an absolute path based on the script's directory.

    Args:
        relative_path (str): Relative path to resolve.

    Returns:
        str: Absolute path.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, relative_path))


def ensure_directory_exists(output_folder):
    """
    Ensures that a specified directory exists, creating it if necessary.

    Args:
        output_folder (str): Path to the directory.
    """
    os.makedirs(output_folder, exist_ok=True)


def ensure_directory_exists_with_date(output_dir):
    """
    Ensures that a dated folder exists under output_dir in the format:
        <output_dir>/<YYYY>/<MM-Mon>/<DD>/

    Args:
        output_dir (str): Base directory where the structure will be created.

    Returns:
        str: Path to the created or existing directory for today’s date.
    """
    current_date = datetime.now()
    year           = current_date.strftime("%Y")
    month_abbrev   = current_date.strftime("%m-%b")  # e.g. "05-May"
    day            = current_date.strftime("%d")

    output_dir_with_date = os.path.join(
        output_dir,
        year,
        month_abbrev,
        day
    )

    os.makedirs(output_dir_with_date, exist_ok=True)

    return output_dir_with_date


# ── PDF Text & Layout Helpers ──
def center_text_x(page, text, fontsize, part=1, total_parts=1):
    """
    Calculates the x-coordinate to center text horizontally on a PDF page.

    Args:
        page (fitz.Page): PDF page object (used for dimensions).
        text (str): Text to center.
        fontsize (int): Font size of the text.
        part (int): Part of the page being centered (used when splitting into columns).
        total_parts (int): Total number of parts (columns) on the page.

    Returns:
        float: x-coordinate for centering the text.
    """
    lines = text.split("\n")  # Split the text into individual lines
    widest_line_width = 0
    font = ImageFont.truetype("arial.ttf", fontsize)

    # Find the widest line in the multi-line text
    for line in lines:
        text_bbox = font.getbbox(line)
        text_width = (
            text_bbox[2] - text_bbox[0]
        )  # Calculate the text width for each line
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
    Adjusts font size to fit text within a specified maximum width.

    Args:
        page (fitz.Page): PDF page object (used for dimensions).
        text (str): Text to fit.
        max_text_width (int): Maximum allowed width for the text.
        max_font_size (int): Starting font size to adjust from.

    Returns:
        int: Adjusted font size.
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


#String Formatting Helpers ──
def format_city_province(city_province_str):
    """
    Formats a city and province string by converting the province name to its abbreviation.

    Status:
        This function is necessary to handle non-standardized inputs in the current database.
        It simplifies downstream processing by ensuring a consistent format for city and province data.

    Args:
        city_province_str (str): Input string in the format "City, Province".

    Returns:
        str: Formatted string in the format "CITY, AB".
             If the input doesn't match the expected format, it is returned unmodified.

    Notes:
        - Ideally, data should already be standardized by customer service, making this function unnecessary.
        - Until input processes are improved, this function provides a reliable workaround for non-standard data.
    """
    province_abbreviations = {
        "Ontario": "ON",
        "Quebec": "QC",
        "British Columbia": "BC",
        "Alberta": "AB",
        "Manitoba": "MB",
        "Saskatchewan": "SK",
        "Nova Scotia": "NS",
        "New Brunswick": "NB",
        "Prince Edward Island": "PE",
        "Newfoundland and Labrador": "NL",
        "Northwest Territories": "NT",
        "Yukon": "YT",
        "Nunavut": "NU",
    }

    match = re.match(r"([A-Za-z\s]+)[, ]*([A-Za-z\s]+)\.?$", city_province_str.strip())
    if not match:
        return city_province_str

    city = match.group(1).strip().upper()
    province = match.group(2).strip()
    if province in province_abbreviations:
        province = province_abbreviations[province]
    province = province.upper()[:2]
    return f"{city}, {province}."


def clean_phone_number(phone_number: str) -> str:
    """
    Cleans and formats a phone number.

    Accepts a variety of input formats (with spaces, dashes, parentheses,
    and extension markers like 'x' or 'ext') and returns:

        "(123) 456-7890"
        "(123) 456-7890 ext. 1234"

    If it can't find a 10-digit number, returns the original string.
    """
    # Try to locate 10 digits + optional extension at the end
    match = re.search(
        r"""
        .*?                    # anything up to...
        (\d{3})\D*            #   area code
        (\d{3})\D*            #   prefix
        (\d{4})               #   line number
        (?:\D*(\d+))?         # optional extension (digits only)
        $                     # end of string
        """,
        phone_number,
        re.VERBOSE,
    )

    if not match:
        return phone_number.strip()

    area, prefix, line, ext = match.groups()
    formatted = f"({area}) {prefix}-{line}"
    if ext:
        formatted += f" ext. {ext}"
    return formatted


def clean_text_refined(text):
    """
    Cleans and formats "Attention to" text, ensuring it contains a proper "ATTN:" prefix and any phone numbers are formatted.

    Args:
        text (str): Text to process, potentially containing an attention prefix or a phone number.

    Returns:
        tuple:
            - str: Cleaned text with "ATTN:" added as a prefix.
            - bool: Flag indicating whether the original text already had "ATTN:".
    """
    cleaned_text = re.sub(r"\s+", " ", text.strip())
    was_attn_present = cleaned_text.startswith("ATTN:")

    cleaned_text = cleaned_text.replace("ATTN:", "").strip()

    phone_number_match = re.search(
        r"(\d{3}[\s-]?\d{3}[\s-]?\d{4}([xXextEXT]*\d+)?)", cleaned_text
    )

    if phone_number_match:
        phone_number_with_ext = phone_number_match.group(1)
        formatted_phone = clean_phone_number(phone_number_with_ext)

        cleaned_text = cleaned_text.replace(phone_number_match.group(0), "").strip()
        cleaned_text = f"{cleaned_text} {formatted_phone}".strip()
    else:
        cleaned_text = cleaned_text

    cleaned_text = f"ATTN: {cleaned_text}"

    return cleaned_text, was_attn_present


def process_order_number(order_number):
    """
    Processes an order number by replacing separators with periods and ensuring a minimum length of 8 characters.

    Args:
        order_number (str): The order number to process.

    Returns:
        str: Processed order number, formatted with periods and added ".00" suffix if not included.
    """
    processed = order_number.replace("-", ".").replace("_", ".")
    return processed if len(processed) >= 8 else processed + ".00"


#Validation Helpers
def validate_alphanumeric(value, field_name):
    """
    Validates if a string is alphanumeric.

    Args:
        value (str): String to validate.
        field_name (str): Name of the field for error messages.

    Returns:
        bool: True if the value is alphanumeric; False otherwise.
    """
    if re.match(r"^[a-zA-Z0-9]+$", value.strip()):
        return True
    else:
        return False


def validate_numeric_field(value, allow_decimal=True):
    """
    Validates whether a field contains a numeric value.

    Args:
        value (str): String to validate.
        allow_decimal (bool): Whether to allow decimal numbers. Defaults to True.

    Returns:
        bool: True if valid; False otherwise.
    """
    try:
        if allow_decimal:
            float(value.strip())
        else:
            int(value.strip())
        return True
    except ValueError:
        return False


def validate_order_number(order_number):
    """
    Validates whether an order number contains only digits and optional periods.

    Args:
        order_number (str): Order number to validate.

    Returns:
        bool: True if valid; False otherwise.
    """
    return bool(re.match(r"^\d+(\.\d{1,2})?$", order_number.strip()))


#Carrier & Skid Logic Helpers
def validate_skid_count(
    carrier_choice,
    skid_count_entry,
    skid_dimensions,
    CARRIER_OPTIONS,
    show_error_message,
):
    """
    Validates the skid count against the entered dimensions, with carrier-specific exceptions.

    Args:
        carrier_choice (int): Index of the selected carrier.
        skid_count_entry (tk.Entry): Entry widget containing the user's skid count.
        skid_dimensions (list): List of entered skid dimensions.
        CARRIER_OPTIONS (dict): Dictionary mapping carrier indices to names.
        show_error_message (function): Function to display an error message dialog.

    Returns:
        bool: True if the skid count is valid; False otherwise.
    """
    try:
        entered_skid_count = int(skid_count_entry.get())

        # Skip validation for Parcel Pro and KPS carriers
        carrier_name = CARRIER_OPTIONS[carrier_choice]
        if carrier_name == "PARCEL PRO":
            # Check if there are any entries in skid_dimensions for Parcel Pro
            if skid_dimensions:
                show_error_message(
                    "Input Restriction",
                    "Parcel Pro only accepts individual items. Please enter the total item count in the 'Cartons' box and remove any skids, carpets, or boxes.",
                )
                return False
            return True

        if carrier_name == "KPS":
            return True

        # Calculate the actual skid count by excluding carpets and boxes
        actual_skid_count = sum(
            1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim
        )

        # Validate if the entered skid count matches the actual skid count
        if entered_skid_count != actual_skid_count:
            show_error_message(
                "Skid Count Mismatch",
                f"Entered skid count is {entered_skid_count}, but the actual number of skids is {actual_skid_count}.",
            )
            return False

        return True

    except ValueError:
        show_error_message("Invalid Input", "Please enter a valid skid count.")
        return False


def validate_carrier_fields(
    carrier_choice,
    tracking_number_entry,
    quote_number_entry,
    quote_price_entry,
    weight_entry,
    CARRIER_OPTIONS,
):
    """
    Validates carrier-specific input fields such as tracking number, quote number, quote price, and weight.

    Args:
        carrier_choice (int): Index of the selected carrier.
        tracking_number_entry (tk.Entry): Entry for the tracking number.
        quote_number_entry (tk.Entry): Entry for the quote number.
        quote_price_entry (tk.Entry): Entry for the quote price.
        weight_entry (tk.Entry): Entry for the weight.
        CARRIER_OPTIONS (dict): Dictionary mapping carrier indices to names.

    Returns:
        bool: True if all fields pass validation; False otherwise.
    """
    carrier_name = CARRIER_OPTIONS.get(carrier_choice, "")

    if carrier_name in ["FF", "NFF"]:
        if not validate_alphanumeric(tracking_number_entry, "Tracking Number"):
            return False
        if not validate_alphanumeric(quote_number_entry, "Quote Number"):
            return False

    if carrier_name in ["FF", "NFF", "FF LOGISTICS", "CRR"]:
        if not validate_numeric_field(quote_price_entry, allow_decimal=True):
            return False

    if carrier_name not in ["KPS", "PARCEL PRO"]:
        if not validate_numeric_field(weight_entry, allow_decimal=True):
            return False

    return True


def get_delivery_instructions(
    inside_var, tailgate_var, appointment_var, two_man_var, white_glove_var
):
    """
    Collects delivery instructions based on user-selected options.

    Args:
        inside_var (tk.BooleanVar): State of "Inside Delivery" checkbox.
        tailgate_var (tk.BooleanVar): State of "Tailgate Delivery" checkbox.
        appointment_var (tk.BooleanVar): State of "Appointment Delivery" checkbox.
        two_man_var (tk.BooleanVar): State of "2-Man Delivery" checkbox.
        white_glove_var (tk.BooleanVar): State of "White Glove Delivery" checkbox.

    Returns:
        list: List of selected delivery instructions.
    """
    instructions = []

    if inside_var.get():
        instructions.append("Inside")
    if tailgate_var.get():
        instructions.append("Tailgate")
    if appointment_var.get():
        instructions.append("Appointment")
    if two_man_var.get():
        instructions.append("2-Man")
    if white_glove_var.get():
        instructions.append("White Glove")

    return instructions
