import re  # For regular expression matching and splitting
import tkinter as tk  # For creating dialog boxes
from utils import validate_alphanumeric, validate_numeric_field

def format_city_province(city_province_str):
    """
    Format the city and province string by converting full province names to abbreviations.
    
    Args:
        city_province_str (str): The city and province string (e.g., "Toronto, Ontario").
        
    Returns:
        str: The formatted city and province string with abbreviations.
    """
    province_abbreviations = {
        'Ontario': 'ON',
        'Quebec': 'QC',
        'British Columbia': 'BC',
        'Alberta': 'AB',
        'Manitoba': 'MB',
        'Saskatchewan': 'SK',
        'Nova Scotia': 'NS',
        'New Brunswick': 'NB',
        'Prince Edward Island': 'PE',
        'Newfoundland and Labrador': 'NL',
        'Northwest Territories': 'NT',
        'Yukon': 'YT',
        'Nunavut': 'NU'
    }

    match = re.match(r"([A-Za-z\s]+)[, ]*([A-Za-z\s]+)\.?$", city_province_str.strip())
    if not match:
        return city_province_str  # Return as is if it doesn't match expected format

    city = match.group(1).strip().upper()
    province = match.group(2).strip()
    if province in province_abbreviations:
        province = province_abbreviations[province]
    province = province.upper()[:2]
    return f"{city}, {province}."


def clean_phone_number(phone_number):
    """
    Clean and format a phone number, removing unnecessary characters and normalizing its format.
    Detect and append the extension if present, using common extension markers like 'x', 'ex', 'ext', etc.
    
    Args:
        phone_number (str): The phone number string.
        
    Returns:
        str: The cleaned and formatted phone number with an extension if present.
    """
    phone_number = re.sub(r'[^0-9xXextEXT]', '', phone_number)

    # Match the phone number part and extension separately
    phone_match = re.match(r'(\d{10})([xXextEXT]*)(\d*)', phone_number)

    if not phone_match:
        return phone_number  # Return as is if the format isn't valid

    main_number = phone_match.group(1)  # Extract the main phone number (first 10 digits)
    extension_marker = phone_match.group(2)  # Extract the extension marker (like 'x' or 'ext')
    extension = phone_match.group(3)  # Extract the extension digits

    # Format the main phone number as (XXX) XXX-XXXX
    formatted_number = f"({main_number[:3]}) {main_number[3:6]}-{main_number[6:]}"

    # Append the extension if found
    if extension:
        formatted_number += f" ext. {extension}"

    return formatted_number


def clean_text_refined(text):
    """
    Clean and refine the 'Attention to' text, ensuring 'ATTN:' is present and that the phone number is formatted.
    
    Args:
        text (str): The text to clean.
        
    Returns:
        tuple: Cleaned text and a flag indicating whether 'ATTN:' was originally present.
    """
    cleaned_text = re.sub(r'\s+', ' ', text.strip())  # Clean up any extra whitespace
    was_attn_present = cleaned_text.startswith("ATTN:")  # Check if 'ATTN:' was originally present

    # Separate the "ATTN:" prefix from the rest of the text
    cleaned_text = cleaned_text.replace("ATTN:", "").strip()

    # Detect and process phone numbers with extensions within the cleaned text
    phone_number_match = re.search(r'(\d{3}[\s-]?\d{3}[\s-]?\d{4}([xXextEXT]*\d+)?)', cleaned_text)
    
    if phone_number_match:
        phone_number_with_ext = phone_number_match.group(1)
        formatted_phone = clean_phone_number(phone_number_with_ext)  # Format the phone number correctly
        # Remove both phone and extension from the main text
        cleaned_text = cleaned_text.replace(phone_number_match.group(0), '').strip()
        cleaned_text = f"{cleaned_text} {formatted_phone}".strip()  # Combine with non-phone text
    else:
        cleaned_text = cleaned_text  # If no phone number, just use the cleaned text

    # Always ensure 'ATTN:' is prefixed to the final cleaned text
    cleaned_text = f"ATTN: {cleaned_text}"

    return cleaned_text, was_attn_present

def validate_skid_count(carrier_choice, skid_count_entry, skid_dimensions, CARRIER_OPTIONS, show_error_message):
    """
    Validate the skid count to ensure it matches the number of skid dimensions entered.
    For KPS, bypass the skid dimension validation and allow direct entry of skid count.
    """
    try:
        # Convert the entry value to an integer
        entered_skid_count = int(skid_count_entry.get())

        # Skip validation for Parcel Pro and KPS carriers
        carrier_name = CARRIER_OPTIONS[carrier_choice]
        if carrier_name == 'PARCEL PRO':
            # Check if there are any entries in skid_dimensions for Parcel Pro
            if skid_dimensions:
                show_error_message(
                    "Input Restriction",
                    "Parcel Pro only accepts individual items. Please enter the total item count in the 'Cartons' box and remove any skids, carpets, or boxes."
                )
                return False  # Return False to indicate validation failure
            return True  # No further validation needed for Parcel Pro
        
        if carrier_name == 'KPS':
            return True  # No further validation needed for KPS

        # Calculate the actual skid count by excluding carpets and boxes
        actual_skid_count = sum(1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim)

        # Validate if the entered skid count matches the actual skid count
        if entered_skid_count != actual_skid_count:
            show_error_message(
                "Skid Count Mismatch", 
                f"Entered skid count is {entered_skid_count}, but the actual number of skids is {actual_skid_count}."
            )
            return False

        return True

    except ValueError:
        show_error_message("Invalid Input", "Please enter a valid skid count.")
        return False


def process_order_number(order_number):
    """
    Process the given order number by replacing dashes or underscores with periods.
    Ensures the processed order number has at least 8 characters by appending ".00" if necessary.
    
    Args:
        order_number (str): The order number to be processed.
        
    Returns:
        str: The processed order number.
    """
    processed = order_number.replace('-', '.').replace('_', '.')
    return processed if len(processed) >= 8 else processed + ".00"

def ask_attention_substitute(contact, phone):
    """
    Display a dialog to ask the user for an attention substitute based on available contact or phone data.

    Args:
        contact (str): The contact person's name.
        phone (str): The contact phone number.

    Returns:
        str: The user's choice for attention substitute.
    """
    cleaned_contact, contact_was_attn_present = clean_text_refined(contact)
    cleaned_phone, phone_was_attn_present = clean_text_refined(phone)

    # Create a new Tkinter dialog box
    root = tk.Toplevel()
    root.title("Attention Information Missing")
    root.geometry("400x250")

    tk.Label(root, text="'Attention to' contents not found in expected location.").pack(pady=5)

    if not contact_was_attn_present or not phone_was_attn_present:
        tk.Label(root, text="Note: [ATTN:] was not in the original field and has been added.").pack(pady=5)

    tk.Label(root, text="Potential substitutes found:").pack(pady=5)

    def use_contact():
        root.choice = cleaned_contact
        root.destroy()

    def use_phone():
        root.choice = cleaned_phone
        root.destroy()

    def leave_blank():
        root.choice = ''
        root.destroy()

    if cleaned_contact:
        contact_display = f"[ATTN:] {cleaned_contact.replace('ATTN:', '').strip()}" if not contact_was_attn_present else cleaned_contact
        tk.Button(root, text=contact_display, command=use_contact).pack(pady=5)

    if cleaned_phone:
        phone_display = f"[ATTN:] {cleaned_phone.replace('ATTN:', '').strip()}" if not phone_was_attn_present else cleaned_phone
        tk.Button(root, text=phone_display, command=use_phone).pack(pady=5)

    tk.Button(root, text="Leave Blank", command=leave_blank).pack(pady=5)

    root.choice = None
    root.grab_set()
    root.wait_window()

    return root.choice

def validate_carrier_fields(carrier_choice, tracking_number_entry, quote_number_entry, quote_price_entry, weight_entry, CARRIER_OPTIONS):
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

def get_delivery_instructions(inside_var, tailgate_var, appointment_var, two_man_var, white_glove_var):
    """
    Gather selected delivery instructions based on the states of checkboxes.
    Args:
        inside_var (tk.BooleanVar): Boolean for 'Inside Delivery'.
        tailgate_var (tk.BooleanVar): Boolean for 'Tailgate Delivery'.
        appointment_var (tk.BooleanVar): Boolean for 'Appointment Delivery'.
        twoman_var (tk.BooleanVar): Boolean for '2-Man Delivery'.
        whiteglove_var (tk.BooleanVar): Boolean for 'White Glove Delivery'.
    Returns:
        list: A list of selected delivery instructions.
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
