import tkinter as tk
import re
from tkinter import messagebox
from tkinter import simpledialog
import logging
import os
import configparser
import fitz



from helpers import (
    format_city_province,
    clean_phone_number,
    clean_text_refined,
    validate_skid_count,
    ask_attention_substitute,
    process_order_number,
    validate_carrier_fields
    )

from utils import validate_alphanumeric, validate_numeric_field, CURRENT_DATE, validate_order_number
from pdf_generator import generate_shipping_label_on_page, generate_labels
from database import fetch_order_data

# Load config.ini for paths and settings
config = configparser.ConfigParser()
config.read('config.ini')

# Fetch paths from config.ini
TEMPLATE_PDF = config['paths']['template_pdf']
OUTPUT_DIR = config['paths']['output_dir']
LOG_FILE_PATH = config['logging']['log_file']

# Convert relative paths to absolute paths
def get_full_path(relative_path):
    """Convert a relative path into an absolute path."""
    return os.path.abspath(os.path.join(os.getcwd(), relative_path))

# Ensure output folder exists
def ensure_directory_exists(output_folder):
    """Ensure that the output directory exists, create it if necessary."""
    os.makedirs(output_folder, exist_ok=True)

# Initialize paths
template_pdf_path = get_full_path(TEMPLATE_PDF)
output_dir_path = get_full_path(OUTPUT_DIR)
log_file_path = get_full_path(LOG_FILE_PATH)

# Ensure the output directory exists
ensure_directory_exists(output_dir_path)

# Logging configuration (dynamic, based on config)
logging.basicConfig(
    filename=log_file_path,
    level=logging.getLevelName(config['logging']['log_level'].upper()),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(message):
    """Log an info message."""
    logging.info(message)

def log_error(message):
    """Log an error message."""
    logging.error(message)

# Initialize the Tkinter root window
root = tk.Tk()
root.title("BOL Generator")
root.geometry("800x800")

# GUI variable initialization
test_mode_var = tk.BooleanVar(value=False)
carrier_var = tk.IntVar(value=0)
classification_var = tk.StringVar(value="Skid")  # Default to Skid



# Define constants for carriers and other options
CARRIER_OPTIONS = {
    1: 'KPS',
    2: 'PARCEL PRO',
    3: 'FF',
    4: 'NFF',
    5: 'FF LOGISTICS',
    6: 'CRR',
    7: 'Other'  # New "Other" option
}

order_numbers = []
skid_dimensions = []


def show_error_message(title, message):
    """Display an error message."""
    messagebox.showerror(title, message)
    log_error(f"{title}: {message}")

def add_order_number(event=None):
    """Add the entered order number to the listbox."""
    order_number = order_number_entry.get().strip()
    
    # Use the new order number validation function
    if validate_order_number(order_number):
        
        # Process the order number to format it correctly (add .00 if needed)
        processed_number = process_order_number(order_number)
        
        # Add the processed order number to the list
        order_numbers.append(processed_number)
        order_listbox.insert(tk.END, processed_number)
        order_number_entry.delete(0, tk.END)
        order_number_entry.focus_set()  # Ensure focus returns to the order number field

        
        log_info(f"Added order number: {processed_number}")
    else:
        show_error_message("Invalid Input", "Order number must be numeric and may include periods (e.g., 123456.00).")


# Initialize the counts at a higher scope (global or class-level)
skid_count = 0
carpet_count = 0
box_count = 0

def add_skid_dimension(event=None):
    """Add the entered skid dimension to the listbox and update counts appropriately."""
    global skid_count, carpet_count, box_count  # Ensure we modify the global variables
    
    dimension_str = skid_dimension_entry.get().strip()
    processed_dimensions = process_skid_dimensions(dimension_str)

    if processed_dimensions:
        # Append classification tags (Skid, Carpet, Box)
        if classification_var.get() == "Carpet":
            processed_dimensions += " (C)"
            carpet_count += 1  # Only increase carpet count
        elif classification_var.get() == "Box":
            processed_dimensions += " (B)"
            box_count += 1  # Only increase box count
        else:
            skid_count += 1  # Only increase skid count for "Skid"
        
        skid_dimensions.append(processed_dimensions)
        skid_listbox.insert(tk.END, processed_dimensions)
        skid_listbox.selection_clear(0, tk.END)
        skid_listbox.selection_set(tk.END)
        skid_dimension_entry.delete(0, tk.END)

        update_skid_count()  # Automatically update the skid count if it's a skid
        log_info(f"Added dimension: {processed_dimensions} | Skid Count: {skid_count}, Carpet Count: {carpet_count}, Box Count: {box_count}")

def update_skid_count():
    """Update the skid count field based on the number of skids (excluding carpets and boxes)."""
    # Only count dimensions marked as skids (exclude carpets and boxes)
    skid_only_count = sum(1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim)
    skid_count_entry.delete(0, tk.END)
    skid_count_entry.insert(0, skid_only_count)  # Update the skid count based on actual skids
    log_info(f"Skid Count Updated: {skid_only_count}")

def process_skid_dimensions(dimension_str):
    """
    Process and validate skid dimensions.
    If input is 6 consecutive digits, it is converted to "12x34x56".
    If input contains non-digit separators like periods or spaces, they are replaced with "x".
    """
    carrier_name = CARRIER_OPTIONS.get(carrier_var.get(), "")
    
    # Skip validation for certain carriers like KPS or PARCEL PRO
    if carrier_name in ['PARCEL PRO']:
        return dimension_str  # Just return the original input without validation

    # Check if the input is exactly 6 digits and parse it into the correct format
    if re.match(r'^\d{6}$', dimension_str):
        return f'{dimension_str[:2]}x{dimension_str[2:4]}x{dimension_str[4:]}'

    # Split by any non-numeric characters and validate
    dimensions = re.split(r'\D+', dimension_str.strip())
    
    # Ensure we get exactly 3 parts and all are digits
    if len(dimensions) != 3 or not all(dim.isdigit() for dim in dimensions):
        show_error_message("Invalid Input", "Please enter exactly three numeric dimensions (e.g., 62x45x33).")
        return None
    
    # Return the dimensions in the "LxWxH" format
    return f"{dimensions[0]}x{dimensions[1]}x{dimensions[2]}"


def update_skid_count():
    """Update the skid count entry."""
    skid_only_count = sum(1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim)
    skid_count_entry.delete(0, tk.END)
    skid_count_entry.insert(0, skid_only_count)
    log_info(f"Updated skid count: {skid_only_count}")

def delete_selected_item():
    """Delete the selected order number or skid dimension from the listbox."""
    if order_listbox.curselection():
        index = order_listbox.curselection()[0]
        deleted_order = order_numbers[index]
        order_listbox.delete(index)
        del order_numbers[index]
        log_info(f"Deleted order number: {deleted_order}")
    elif skid_listbox.curselection():
        index = skid_listbox.curselection()[0]
        deleted_dimension = skid_dimensions[index]
        skid_listbox.delete(index)
        del skid_dimensions[index]
        update_skid_count()
        log_info(f"Deleted skid dimension: {deleted_dimension}")

def validate_inputs():
    carrier_choice = carrier_var.get()

    if not validate_carrier_fields(
        carrier_choice,
        tracking_number_entry.get().strip(),  # Pass the string from Entry
        quote_number_entry.get().strip(),     # Pass the string from Entry
        quote_price_entry.get().strip(),      # Pass the string from Entry
        weight_entry.get().strip(),           # Pass the string from Entry
        CARRIER_OPTIONS  # Correct, now it has only 6 arguments
    ):
        show_error_message("Invalid Input", "Carrier-specific validation failed. Please check your input.")


    # Validate skid count
    if not validate_skid_count(carrier_choice, skid_count_entry, skid_dimensions, CARRIER_OPTIONS, show_error_message):
        return False

    log_info("Input validation successful.")
    return True

def select_carrier_and_generate():
    """
    Generate the BOL PDF and update the database based on the input.
    """

    from pdf_generator import generate_bol, prepare_data_map
    from helpers import validate_skid_count, clean_text_refined
    from utils import ensure_directory_exists_with_date
    from database import update_shipping_data  # Ensure this is imported

    log_info("Starting BOL generation process.")

    # Validate the inputs before proceeding
    if not validate_inputs():
        return

    # Gather user inputs
    carrier_choice = carrier_var.get()  # Get the selected carrier

    # Check if "Other" carrier is selected
    if carrier_choice == 7:  # Assuming "Other" carrier is mapped to 7
        carrier_name = simpledialog.askstring("Input", "Enter carrier name:").upper()  # Convert to all caps
        if not carrier_name:
            show_error_message("Carrier Selection Error", "Carrier name cannot be empty.")
            return
    else:
        if carrier_choice not in CARRIER_OPTIONS:
            show_error_message("Carrier Selection Error", "Please select a valid carrier.")
            return
        carrier_name = CARRIER_OPTIONS[carrier_choice]  # Get the carrier name

    skid_count_entry_value = skid_count_entry.get().strip()  # Get the skid count entry value
    skid_count = int(skid_count_entry_value)  # Convert to integer
    skid_cartons = int(skid_cartons_entry.get().strip())  # Get the number of cartons for skids
    quote_number = quote_number_entry.get().strip()  # Get the quote number from GUI
    quote_price = quote_price_entry.get().strip()  # Get the quote price from GUI
    weight = weight_entry.get().strip()  # Get the weight from GUI
    skid_dimensions = [entry for entry in skid_listbox.get(0, tk.END)]  # Get skid dimensions from the listbox

    # Automatically set the tracking number to the first order number if not FF/NFF
    if carrier_name not in ['FF', 'NFF']:
        tracking_number = order_numbers[0]  # Use the first order number as the tracking number
    else:
        tracking_number = tracking_number_entry.get().strip()  # Get the tracking number manually

    # Validate skid count
    if not validate_skid_count(
        carrier_choice,
        skid_count_entry,  # Pass the entry widget itself
        skid_dimensions,
        CARRIER_OPTIONS,
        show_error_message):
        return

    # Ensure `order_numbers` is populated (this may have been missed)
    if not order_numbers:  # Ensure this is populated before usage
        show_error_message("Error", "Please enter at least one order number.")
        return

    # Fetch order data based on the first order number
    result = fetch_order_data(order_numbers[0])
    if not result:
        show_error_message("Error", f"No record found for Order Number: {order_numbers[0]}")
        return

    # Prepare the data map using the helper function
    data_map = prepare_data_map(
        result,
        skid_count,
        carpet_count,
        box_count,
        skid_cartons,
        order_numbers,  # Ensure this is passed correctly
        carrier_name,
        quote_number,
        quote_price,
        tracking_number,
        weight,
        skid_dimensions
    )

    # Ensure the output directory exists and has the proper date-based folder structure
    output_folder_with_date = ensure_directory_exists_with_date(output_dir_path)

    # Generate BOL PDF
    output_pdf_filled = generate_bol(
        result,
        carrier_name,
        tracking_number,
        skid_count,
        carpet_count,
        box_count,
        skid_cartons,
        output_folder_with_date,  # Pass the correct output folder with date
        skid_dimensions,
        order_numbers,
        quote_number,
        quote_price,
        weight
    )

    if output_pdf_filled:
        log_info(f"PDF generated successfully: {output_pdf_filled}")

        # Loop through each order number and update shipping data in ODBC
        for order_number in order_numbers:
            # Log the details of what is being uploaded to ODBC
            log_info(f"Preparing to upload data to ODBC for Order Number: {order_number}")
            log_info(f"Carrier Name: {carrier_name}")
            log_info(f"Tracking Number: {tracking_number}")
            log_info(f"Skid Dimensions: {skid_dimensions}")
            log_info(f"Skid Count: {skid_count}")
            log_info(f"Weight: {weight}")

            # Upload data to ODBC
            update_shipping_data(order_number, carrier_name, tracking_number, skid_dimensions, skid_count, weight)

            log_info(f"Successfully updated shipping data for Order Number: {order_number}")
    else:
        show_error_message("Error", "Failed to generate the PDF.")
        log_error("PDF generation failed.")


def edit_selected_item():
    """
    Edit the selected order number or skid dimension in the listbox.
    """
    if order_listbox.curselection():
        index = order_listbox.curselection()[0]
        order_number_entry.delete(0, tk.END)
        order_number_entry.insert(0, order_numbers[index])

        def update_order(event=None):
            new_value = order_number_entry.get().strip()
            if re.match(r'^\d+(\.|-|_)?\d*$', new_value):
                order_numbers[index] = process_order_number(new_value)
                order_listbox.delete(index)
                order_listbox.insert(index, order_numbers[index])
                order_listbox.selection_clear(0, tk.END)
                order_listbox.selection_set(index)
                order_number_entry.delete(0, tk.END)
                edit_button.config(text="Edit", command=edit_selected_item)
                order_number_entry.bind("<Return>", add_order_number)
            else:
                show_error_message("Invalid Input", "Please enter a valid order number.")

        edit_button.config(text="Update", command=update_order)
        order_number_entry.bind("<Return>", update_order)

    elif skid_listbox.curselection():
        index = skid_listbox.curselection()[0]
        skid_text = skid_dimensions[index]

        # Detect whether it's a Carpet or Box
        if "(C)" in skid_text:
            skid_text = skid_text.replace(" (C)", "")
            classification_var.set("Carpet")
        elif "(B)" in skid_text:
            skid_text = skid_text.replace(" (B)", "")
            classification_var.set("Box")
        else:
            classification_var.set("Skid")

        skid_dimension_entry.delete(0, tk.END)
        skid_dimension_entry.insert(0, skid_text)

        def update_skid(event=None):
            new_value = skid_dimension_entry.get().strip()
            processed_value = process_skid_dimensions(new_value)
            if processed_value:
                # Append classification tag (Skid, Carpet, Box)
                if classification_var.get() == "Carpet":
                    processed_value += " (C)"
                elif classification_var.get() == "Box":
                    processed_value += " (B)"
                skid_dimensions[index] = processed_value
                skid_listbox.delete(index)
                skid_listbox.insert(index, processed_value)
                skid_listbox.selection_clear(0, tk.END)
                skid_listbox.selection_set(index)
                skid_dimension_entry.delete(0, tk.END)
                edit_button.config(text="Edit", command=edit_selected_item)
                skid_dimension_entry.bind("<Return>", add_skid_dimension)
                update_skid_count()

        edit_button.config(text="Update", command=update_skid)
        skid_dimension_entry.bind("<Return>", update_skid)

# Clear all input fields
def clear_contents():
    """Clear the contents of all input fields."""
    order_number_entry.delete(0, tk.END)
    order_listbox.delete(0, tk.END)
    skid_dimension_entry.delete(0, tk.END)
    skid_listbox.delete(0, tk.END)
    tracking_number_entry.delete(0, tk.END)
    weight_entry.delete(0, tk.END)
    skid_cartons_entry.delete(0, tk.END)
    skid_count_entry.delete(0, tk.END)
    quote_price_entry.delete(0, tk.END)
    quote_number_entry.delete(0, tk.END)
    order_numbers.clear()
    skid_dimensions.clear()
    log_info("Cleared all input fields.")

# Setting up the GUI components
frame_left = tk.Frame(root)
frame_right = tk.Frame(root)
frame_left.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
frame_right.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

# Order Number Section
tk.Label(frame_left, text="Order Number:").pack(pady=5)
order_number_entry = tk.Entry(frame_left)
order_number_entry.pack(pady=5)
order_number_entry.bind("<Return>", add_order_number)

tk.Button(frame_left, text="Add Order Number", command=add_order_number).pack(pady=5)

tk.Label(frame_left, text="Order Numbers:").pack(pady=5)
order_listbox = tk.Listbox(frame_left, height=30)  # Expanded vertically for more space
order_listbox.pack(pady=5)

# Skid Dimensions Section
tk.Label(frame_right, text="Dimension (LxWxH):").pack(pady=5)
skid_dimension_entry = tk.Entry(frame_right)
skid_dimension_entry.pack(pady=5)
skid_dimension_entry.bind("<Return>", add_skid_dimension)

tk.Button(frame_right, text="Add Dimension", command=add_skid_dimension).pack(pady=5)

# Move the Skid/Carpet/Box Classification radio buttons under the dimension entry for compact layout
classification_frame = tk.Frame(frame_right)
classification_frame.pack(pady=5)
tk.Radiobutton(classification_frame, text="Skid", variable=classification_var, value="Skid").pack(side=tk.LEFT)
tk.Radiobutton(classification_frame, text="Carpet", variable=classification_var, value="Carpet").pack(side=tk.LEFT)
tk.Radiobutton(classification_frame, text="Box", variable=classification_var, value="Box").pack(side=tk.LEFT)

tk.Label(frame_right, text="Dimensions:").pack(pady=5)
skid_listbox = tk.Listbox(frame_right, height=30)  # Expanded vertically for more space
skid_listbox.pack(pady=5)

# Skid Count Section
tk.Label(frame_right, text="Skid Count:").pack(pady=5)
skid_count_entry = tk.Entry(frame_right, width=5)
skid_count_entry.pack(pady=5)

# Carrier Selection Section
tk.Label(root, text="Select Carrier:").pack(pady=10)
for key, value in CARRIER_OPTIONS.items():
    tk.Radiobutton(root, text=value, variable=carrier_var, value=key).pack(anchor=tk.W)

# Tracking Number Section
tk.Label(root, text="Tracking Number:").pack(pady=5)
tracking_number_entry = tk.Entry(root)
tracking_number_entry.pack(pady=5)

# Weight Entry Section
tk.Label(root, text="Weight:").pack(pady=5)
weight_entry = tk.Entry(root)
weight_entry.pack(pady=5)

# Quote Number Section
tk.Label(root, text="Quote #:").pack(pady=5)
quote_number_entry = tk.Entry(root)
quote_number_entry.pack(pady=5)

# Cartons Section
tk.Label(root, text="Cartons:").pack(pady=5)
skid_cartons_entry = tk.Entry(root)
skid_cartons_entry.pack(pady=5)

# Quote Price Section
tk.Label(root, text="Quote Price:").pack(pady=5)
quote_price_entry = tk.Entry(root)
quote_price_entry.pack(pady=5)

# Generate PDF and Clear All Buttons (no space between them)
tk.Button(root, text="Generate PDF", command=select_carrier_and_generate).pack(pady=5)
tk.Button(root, text="Clear All", command=clear_contents).pack(pady=5)

# Add the Edit and Delete buttons to the GUI, aligned with other buttons
edit_button = tk.Button(root, text="Edit", command=edit_selected_item)
edit_button.pack(pady=5)
delete_button = tk.Button(root, text="Delete", command=delete_selected_item)
delete_button.pack(pady=5)

order_number_entry.focus_set()  # Focus the order number entry on startup

# Run the Tkinter main loop
root.mainloop()