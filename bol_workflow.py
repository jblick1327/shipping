import tkinter as tk
from tkinter import simpledialog
from database import fetch_order_data, update_shipping_data
from utils import ensure_directory_exists_with_date, get_delivery_instructions
from pdf_generator import generate_bol


def choose_carrier(
    carrier_choice: int, carrier_options: dict[int, str], show_error: callable
) -> str | None:
    """
    Step 2: Carrier Selection
    Returns the carrier name string, or None if invalid / cancelled.
    """
    # Custom carrier
    if carrier_choice == max(carrier_options):
        carrier_name = simpledialog.askstring("Input", "Enter carrier name:")
        if not carrier_name:
            show_error("Carrier Selection Error", "Carrier name cannot be empty.")
            return None
        return carrier_name.upper()
    # Predefined carrier
    if carrier_choice not in carrier_options:
        show_error("Carrier Selection Error", "Please select a valid carrier.")
        return None
    return carrier_options[carrier_choice]


def get_order_record(order_numbers: list[str], show_error: callable) -> dict | None:
    """
    Step 3: Data Fetching
    Returns the DB record dict for the first order number, or None if missing/error.
    """
    if not order_numbers:
        show_error("Order Number Error", "Please enter at least one order number.")
        return None

    record = fetch_order_data(order_numbers[0])
    if not record:
        show_error(
            "Order Data Error", f"No record found for Order Number: {order_numbers[0]}"
        )
        return None

    return record


def collect_ui_inputs(
    order_numbers: list[str],
    tracking_entry: tk.Entry,
    skid_count_entry: tk.Entry,
    skid_cartons_entry: tk.Entry,
    quote_num_entry: tk.Entry,
    quote_price_entry: tk.Entry,
    weight_entry: tk.Entry,
    skid_listbox: tk.Listbox,
    selected_date_var: tk.StringVar,
    inside_var: tk.BooleanVar,
    tailgate_var: tk.BooleanVar,
    appointment_var: tk.BooleanVar,
    two_man_var: tk.BooleanVar,
    white_glove_var: tk.BooleanVar,
    carrier_name: str,
    show_error: callable,
) -> dict | None:
    """
    Gathers and validates all UI inputs, returns a flat dict of values or None on error.
    """
    try:
        tracking = tracking_entry.get().strip()
        skid_count = int(skid_count_entry.get().strip())
        skid_cartons = int(skid_cartons_entry.get().strip())
        quote_num = quote_num_entry.get().strip()
        quote_price = quote_price_entry.get().strip()
        weight = weight_entry.get().strip()
    except ValueError:
        show_error(
            "Input Error",
            "Numeric fields (skid count, cartons) must be valid integers.",
        )
        return None

    dims = [skid_listbox.get(i) for i in range(skid_listbox.size())]
    carpet_count = sum(1 for d in dims if "(C)" in d)
    box_count = sum(1 for d in dims if "(B)" in d)

    # Delivery instructions split
    instructions = get_delivery_instructions(
        inside_var, tailgate_var, appointment_var, two_man_var, white_glove_var
    )
    if len(instructions) <= 3:
        add_info_7 = ""
        add_info_8 = ", ".join(instructions) + " Delivery"
    else:
        add_info_7 = ", ".join(instructions[:2]) + ","
        add_info_8 = ", ".join(instructions[2:]) + " Delivery"

    return {
        "order_numbers": order_numbers,
        "tracking_number": tracking if carrier_name not in ["FF", "NFF"] else tracking,
        "skid_count": skid_count,
        "carpet_count": carpet_count,
        "box_count": box_count,
        "skid_cartons": skid_cartons,
        "quote_number": quote_num,
        "quote_price": quote_price,
        "weight": weight,
        "skid_dimensions": dims,
        "shipping_date": selected_date_var.get(),
        "add_info_7": add_info_7,
        "add_info_8": add_info_8,
    }


def build_and_save_pdfs(
    record: dict,
    inputs: dict,
    output_dir: str,
    log_info: callable,
    show_error: callable,
) -> str | None:
    """
    Step 4: PDF Generation
    Generates the BOL and label PDFs, returns the BOL path or None on failure.
    """
    # ensure dated folder exists
    folder = ensure_directory_exists_with_date(output_dir)
    log_info(f"Using output folder: {folder}")

    bol_path = generate_bol(
        result=record,
        carrier_name=inputs["carrier_name"],
        tracking_number=inputs["tracking_number"],
        skid_count=inputs["skid_count"],
        carpet_count=inputs["carpet_count"],
        box_count=inputs["box_count"],
        skid_cartons=inputs["skid_cartons"],
        output_folder=folder,
        skid_dimensions=inputs["skid_dimensions"],
        order_numbers=inputs["order_numbers"],
        quote_number=inputs["quote_number"],
        quote_price=inputs["quote_price"],
        weight=inputs["weight"],
        add_info_7=inputs["add_info_7"],
        add_info_8=inputs["add_info_8"],
    )
    if not bol_path:
        show_error("Error", "Failed to generate the PDF.")
    else:
        log_info(f"PDF generated: {bol_path}")
    return bol_path


def update_database_for_orders(
    order_numbers: list[str],
    tracking_number: str,
    carrier_name: str,
    weight: str,
    skid_cartons: int,
    quote_price: str,
    log_info: callable,
):
    """
    Step 5: Database Update
    Calls update_shipping_data for each order in the list.
    """
    for num in order_numbers:
        log_info(f"Updating DB for order {num}")
        update_shipping_data(
            num, tracking_number, carrier_name, weight, skid_cartons, quote_price
        )
        log_info(f"DB updated for order {num}")
