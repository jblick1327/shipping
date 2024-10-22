import tkinter as tk
import re
from tkcalendar import Calendar
from tkinter import messagebox, simpledialog
import logging
import os
import configparser
from datetime import datetime

from helpers import (
    validate_skid_count,
    process_order_number,
    validate_carrier_fields,
    get_delivery_instructions
    )

from utils import validate_order_number, CURRENT_DATE
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
    """Convert a relative file path into an absolute path using the current working directory."""
    return os.path.abspath(os.path.join(os.getcwd(), relative_path))

# Ensure output directory exists
def ensure_directory_exists(output_folder):
    """Ensure that the specified output directory exists. If it does not exist, create it."""
    os.makedirs(output_folder, exist_ok=True)

# Initialize paths for template, output directory, and log file
template_pdf_path = get_full_path(TEMPLATE_PDF)
output_dir_path = get_full_path(OUTPUT_DIR)
log_file_path = get_full_path(LOG_FILE_PATH)

# Ensure the output directory exists
ensure_directory_exists(output_dir_path)

# Configure logging using settings from the config file
logging.basicConfig(
    filename=log_file_path,
    level=logging.getLevelName(config['logging']['log_level'].upper()),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(message):
    """Log an informational message to the log file."""
    logging.info(message)

def log_error(message):
    """Log an error message to the log file."""
    logging.error(message)

# Initialize the Tkinter root window for the application
root = tk.Tk()
root.title("BOL Generator")
root.geometry("800x1000")

def open_calendar_popup():
    """Open a popup window with a calendar to select a shipping date."""
    def on_date_selected():
        """Handle the event when a date is selected from the calendar."""
        selected_date = calendar.get_date()
        # Convert selected date to "YYYY-MM-DD" format
        formatted_date = datetime.strptime(selected_date, '%m/%d/%y').strftime('%Y-%m-%d')
        selected_date_var.set(formatted_date)  # Update the variable with the formatted date
        top.destroy()  # Close the popup window

    top = tk.Toplevel(root)
    calendar = Calendar(top, selectmode='day', year=2024, month=10, day=16)
    calendar.pack(pady=10)

    select_button = tk.Button(top, text="Select", command=on_date_selected)
    select_button.pack(pady=5)

# Initialize GUI variables
carrier_var = tk.IntVar(value=0)  # Stores the selected carrier
classification_var = tk.StringVar(value="Skid")  # Default classification is "Skid"

# Shipping Date Variables
selected_date_var = tk.StringVar()
selected_date_var.set(CURRENT_DATE)  # Default date is set to current date

# Delivery Instructions Variables
inside_var = tk.BooleanVar(value=True)  # Default: Inside Delivery is checked
tailgate_var = tk.BooleanVar(value=True)  # Default: Tailgate Delivery is checked
appointment_var = tk.BooleanVar(value=False)  # Default: Appointment Delivery is unchecked
two_man_var = tk.BooleanVar(value=False)  # Default: 2-Man Delivery is unchecked
white_glove_var = tk.BooleanVar(value=False)  # Default: White Glove Delivery is unchecked

# Carrier options dictionary for radio buttons
CARRIER_OPTIONS = {
    1: 'KPS',
    2: 'PARCEL PRO',
    3: 'FF',
    4: 'NFF',
    5: 'FF LOGISTICS',
    6: 'CRR',
    7: 'Other'  # "Other" allows user input for custom carrier names
}

# Lists to hold order numbers and skid dimensions
order_numbers = []
skid_dimensions = []

def show_error_message(title, message):
    """Display an error message using a messagebox and log the error."""
    messagebox.showerror(title, message)
    log_error(f"{title}: {message}")

def add_order_number(event=None):
    """Add a validated order number to the order listbox."""
    order_number = order_number_entry.get().strip()

    # Validate the order number format
    if validate_order_number(order_number):
        # Format the order number (e.g., add ".00" if needed)
        processed_number = process_order_number(order_number)
        
        # Append to the list of order numbers
        order_numbers.append(processed_number)
        order_listbox.insert(tk.END, processed_number)
        
        # Clear the entry field and refocus for convenience
        order_number_entry.delete(0, tk.END)
        order_number_entry.focus_set()
        
        log_info(f"Added order number: {processed_number}")
    else:
        show_error_message("Invalid Input", "Order number must be numeric and may include periods (e.g., 123456.00).")

# Global counters for tracking item counts
skid_count = 0
carpet_count = 0
box_count = 0

def add_skid_dimension(event=None):
    """Add a validated skid dimension to the skid dimensions listbox and update counts."""
    global skid_count, carpet_count, box_count  # Update global counters

    carrier_name = CARRIER_OPTIONS.get(carrier_var.get(), "")
    
    # Restrict skid shipments for specific carriers (e.g., PARCEL PRO)
    if carrier_name == 'PARCEL PRO' and classification_var.get() == "Skid":
        show_error_message("Invalid Operation", "PARCEL PRO does not support Skid shipments.")
        return

    dimension_str = skid_dimension_entry.get().strip()
    processed_dimensions = process_skid_dimensions(dimension_str)

    if processed_dimensions:
        # Tag the dimension with its classification (Skid, Carpet, Box)
        if classification_var.get() == "Carpet":
            processed_dimensions += " (C)"
            carpet_count += 1
        elif classification_var.get() == "Box":
            processed_dimensions += " (B)"
            box_count += 1
        else:
            skid_count += 1  # Default to "Skid"

        # Append dimension to the list and update the display
        skid_dimensions.append(processed_dimensions)
        skid_listbox.insert(tk.END, processed_dimensions)
        skid_dimension_entry.delete(0, tk.END)

        # Update the skid count if applicable
        update_skid_count()
        log_info(f"Added dimension: {processed_dimensions} | Skid Count: {skid_count}, Carpet Count: {carpet_count}, Box Count: {box_count}")

def process_skid_dimensions(dimension_str):
    """
    Validate and process the input string for skid dimensions.
    - If input is 6 digits (e.g., "123456"), convert it to "12x34x56".
    - Replace non-digit characters with "x" to format dimensions correctly.
    """
    carrier_name = CARRIER_OPTIONS.get(carrier_var.get(), "")

    # Skip validation for certain carriers (e.g., PARCEL PRO)
    if carrier_name == 'PARCEL PRO':
        return dimension_str

    # Check for 6 consecutive digits and convert to "LxWxH" format
    if re.match(r'^\d{6}$', dimension_str):
        return f'{dimension_str[:2]}x{dimension_str[2:4]}x{dimension_str[4:]}'

    # Split by non-digit characters and validate each part
    dimensions = re.split(r'\D+', dimension_str.strip())

    # Ensure exactly 3 parts (LxWxH) are provided, all of which are numeric
    if len(dimensions) != 3 or not all(dim.isdigit() for dim in dimensions):
        show_error_message("Invalid Input", "Please enter exactly three numeric dimensions (e.g., 62x45x33).")
        return None

    # Return dimensions in "LxWxH" format
    return f"{dimensions[0]}x{dimensions[1]}x{dimensions[2]}"

def update_skid_count():
    """Update the displayed skid count (excluding carpets and boxes)."""
    skid_only_count = sum(1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim)
    skid_count_entry.delete(0, tk.END)
    skid_count_entry.insert(0, skid_only_count)
    log_info(f"Updated skid count: {skid_only_count}")

def delete_selected_item():
    """Delete the selected item (order number or skid dimension) from the respective listbox."""
    if order_listbox.curselection():
        # Delete the selected order number
        index = order_listbox.curselection()[0]
        deleted_order = order_numbers[index]
        order_listbox.delete(index)
        del order_numbers[index]
        log_info(f"Deleted order number: {deleted_order}")
    elif skid_listbox.curselection():
        # Delete the selected skid dimension
        index = skid_listbox.curselection()[0]
        deleted_dimension = skid_dimensions[index]
        skid_listbox.delete(index)
        del skid_dimensions[index]
        update_skid_count()
        log_info(f"Deleted skid dimension: {deleted_dimension}")

def validate_inputs():
    """Validate all required inputs before proceeding with BOL generation."""
    carrier_choice = carrier_var.get()

    # Perform carrier-specific validation
    if not validate_carrier_fields(
        carrier_choice,
        tracking_number_entry.get().strip(),
        quote_number_entry.get().strip(),
        quote_price_entry.get().strip(),
        weight_entry.get().strip(),
        CARRIER_OPTIONS
    ):
        show_error_message("Invalid Input", "Carrier-specific validation failed. Please check your input.")

    # Validate the skid count
    if not validate_skid_count(carrier_choice, skid_count_entry, skid_dimensions, CARRIER_OPTIONS, show_error_message):
        return False

    log_info("Input validation successful.")
    return True

def select_carrier_and_generate():
    """
    Generate the BOL PDF and update shipping data in the database based on user inputs.
    This function validates the inputs, gathers the required data, and performs the necessary operations.
    """
    from pdf_generator import generate_bol, prepare_data_map
    from helpers import validate_skid_count, clean_text_refined
    from utils import ensure_directory_exists_with_date
    from database import update_shipping_data

    log_info("Starting BOL generation process.")

    # Validate the inputs before proceeding
    if not validate_inputs():
        return

    # Gather the selected carrier and other user inputs
    carrier_choice = carrier_var.get()
    if carrier_choice == 7:  # Custom carrier option
        carrier_name = simpledialog.askstring("Input", "Enter carrier name:").upper()
        if not carrier_name:
            show_error_message("Carrier Selection Error", "Carrier name cannot be empty.")
            return
    else:
        if carrier_choice not in CARRIER_OPTIONS:
            show_error_message("Carrier Selection Error", "Please select a valid carrier.")
            return
        carrier_name = CARRIER_OPTIONS[carrier_choice]

    # Process the rest of the input data
    skid_count_entry_value = skid_count_entry.get().strip()
    skid_count = int(skid_count_entry_value)
    skid_cartons = int(skid_cartons_entry.get().strip())
    quote_number = quote_number_entry.get().strip()
    quote_price = quote_price_entry.get().strip()
    weight = weight_entry.get().strip()
    skid_dimensions = [entry for entry in skid_listbox.get(0, tk.END)]
    tracking_number = order_numbers[0] if carrier_name not in ['FF', 'NFF'] else tracking_number_entry.get().strip()

    # Validate the skid count again
    if not validate_skid_count(carrier_choice, skid_count_entry, skid_dimensions, CARRIER_OPTIONS, show_error_message):
        return

    if not order_numbers:
        show_error_message("Error", "Please enter at least one order number.")
        return

    # Fetch order data for the first order number
    result = fetch_order_data(order_numbers[0])
    if not result:
        show_error_message("Error", f"No record found for Order Number: {order_numbers[0]}")
        return

    # Get selected shipping date and delivery instructions
    shipping_date = selected_date_var.get()
    delivery_instructions = get_delivery_instructions(inside_var, tailgate_var, appointment_var, two_man_var, white_glove_var)
    add_info_7 = ", ".join(delivery_instructions[:2])
    if add_info_7:  
        add_info_7 += ","
    
    add_info_8 = ", ".join(delivery_instructions[2:]) + " Delivery"

    # Prepare the data map for the PDF generation
    data_map = prepare_data_map(
        result,
        skid_count,
        carpet_count,
        box_count,
        skid_cartons,
        order_numbers,
        carrier_name,
        quote_number,
        quote_price,
        tracking_number,
        weight,
        skid_dimensions,
        add_info_7,  # AddInfo7
        add_info_8   # AddInfo8
    )
    data_map['Date'] = shipping_date

    # Ensure the output directory exists (organized by date)
    output_folder_with_date = ensure_directory_exists_with_date(output_dir_path)

    # Generate the BOL PDF and update the shipping data
    output_pdf_filled = generate_bol(
        result,
        carrier_name,
        tracking_number,
        skid_count,
        carpet_count,
        box_count,
        skid_cartons,
        output_folder_with_date,
        skid_dimensions,
        order_numbers,
        quote_number,
        quote_price,
        weight,
        add_info_7,  # Pass AddInfo7
        add_info_8   # Pass AddInfo8
    )

    if output_pdf_filled:
        log_info(f"PDF generated successfully: {output_pdf_filled}")

        # Update the shipping data for each order number in the database
        for order_number in order_numbers:
            log_info(f"Updating shipping data for Order Number: {order_number}")
            update_shipping_data(order_number, carrier_name, tracking_number, skid_dimensions, skid_count, weight)
            log_info(f"Successfully updated shipping data for Order Number: {order_number}")
    else:
        show_error_message("Error", "Failed to generate the PDF.")
        log_error("PDF generation failed.")

def edit_selected_item():
    """Edit the selected item (order number or skid dimension) in the listbox."""
    if order_listbox.curselection():
        # Edit order number
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
        # Edit skid dimension
        index = skid_listbox.curselection()[0]
        skid_text = skid_dimensions[index]

        # Determine classification (Skid, Carpet, Box) and remove tags for editing
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
                # Reapply classification tag
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

def clear_contents():
    """Clear the contents of all input fields and reset variables."""
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
    selected_date_var.set(CURRENT_DATE)
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

# Delivery Instructions Section
tk.Label(root, text="Delivery Instructions:").pack(pady=5)

# Shipping Date Selection (button to open calendar popup)
tk.Button(root, text="Select Shipping Date", command=open_calendar_popup).pack(pady=5)

# Label to display the selected shipping date
tk.Label(root, textvariable=selected_date_var).pack(pady=5)

tk.Checkbutton(root, text="Inside Delivery", variable=inside_var).pack(anchor=tk.W)
tk.Checkbutton(root, text="Tailgate Delivery", variable=tailgate_var).pack(anchor=tk.W)
tk.Checkbutton(root, text="Appointment Delivery", variable=appointment_var).pack(anchor=tk.W)
tk.Checkbutton(root, text="2-Man Delivery", variable=two_man_var).pack(anchor=tk.W)
tk.Checkbutton(root, text="White Glove Delivery", variable=white_glove_var).pack(anchor=tk.W)

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
