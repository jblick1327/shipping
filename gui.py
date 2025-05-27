"""
This module is the main script for the application, providing a graphical user interface (GUI) for generating Bills of Lading (BOL).
"""

# Standard library
import re
import tkinter as tk
from datetime import datetime
import argparse

# 3rd-party
from tkcalendar import Calendar
from tkinter import messagebox


# Local modules
from utils import (
    get_logger,
    CURRENT_DATE,
    validate_order_number,
    validate_skid_count,
    process_order_number,
    validate_carrier_fields,
    load_config,
    get_full_path,
)
from bol_workflow import (
    choose_carrier,
    get_order_record,
    collect_ui_inputs,
    build_and_save_pdfs,
    update_database_for_orders,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--scale",
    type=float,
    default=1.0,
    help="Global UI scaling factor (e.g. 0.8 for 80%, 1.2 for 120%)"
)
args = parser.parse_args()

def make_labeled_entry(parent, label_text, **opts):
    tk.Label(parent, text=label_text).pack(pady=5)
    e = tk.Entry(parent, **opts)
    e.pack(pady=5)
    return e


def make_checkbox(parent, text, var):
    tk.Checkbutton(parent, text=text, variable=var).pack(anchor=tk.W, pady=2)


def make_button(parent, text, command, **opts):
    btn = tk.Button(parent, text=text, command=command, **opts)
    btn.pack(pady=5)
    return btn


def make_listbox_section(parent, label_text, height=10):
    tk.Label(parent, text=label_text).pack(pady=5)
    lb = tk.Listbox(parent, height=height)
    lb.pack(pady=5)
    return lb


config = load_config()
output_dir_path = get_full_path(config["paths"]["output_dir"])
logger = get_logger(__name__)


def main():
    root = tk.Tk()
    root.title("BOL Generator")
    root.tk.call('tk', 'scaling', args.scale)
    root.geometry("800x1000")

    def open_calendar_popup():
        """
        Opens a popup window with a calendar for the user to select a shipping date.

        The selected date is returned in "YYYY-MM-DD" format.
        """

        def on_date_selected():
            """Handle the event when a date is selected from the calendar."""
            selected_date = calendar.get_date()
            formatted_date = datetime.strptime(selected_date, "%m/%d/%y").strftime(
                "%Y-%m-%d"
            )
            selected_date_var.set(formatted_date)
            top.destroy()

        top = tk.Toplevel(root)
        today = datetime.now()
        calendar = Calendar(
            top, selectmode="day", year=today.year, month=today.month, day=today.day
        )
        calendar.pack(pady=10)

        select_button = tk.Button(top, text="Select", command=on_date_selected)
        select_button.pack(pady=5)

    # Initialize GUI variables
    carrier_var = tk.IntVar(value=0)
    classification_var = tk.StringVar(value="Skid")

    # Shipping Date Variables
    selected_date_var = tk.StringVar()
    selected_date_var.set(CURRENT_DATE)  # Default date is set to current date

    # Delivery Instructions Variables
    inside_var = tk.BooleanVar(value=True)  # Default: Inside Delivery is checked
    tailgate_var = tk.BooleanVar(value=True)  # Default: Tailgate Delivery is checked
    appointment_var = tk.BooleanVar(
        value=False
    )  # Default: Appointment Delivery is unchecked
    two_man_var = tk.BooleanVar(value=False)  # Default: 2-Man Delivery is unchecked
    white_glove_var = tk.BooleanVar(
        value=False
    )  # Default: White Glove Delivery is unchecked

    # Carrier options dictionary for radio buttons
    CARRIER_OPTIONS = {
        1: "KPS",
        2: "PARCEL PRO",
        3: "FF",
        4: "NFF",
        5: "FF LOGISTICS",
        6: "CRR",
        7: "Other",  # "Other" allows user input for custom carrier names
    }

    order_numbers = []
    skid_dimensions = []

    def show_error_message(title, message):
        """
        Displays an error message dialog and logs the error.

        Args:
            title (str): Title of the error dialog.
            message (str): Detailed error message to display.
        """
        messagebox.showerror(title, message)
        logger.error(f"{title}: {message}")

    def add_order_number(event=None):
        """
        Adds a validated order number to the order list and displays it in the listbox.

        Args:
            event (tk.Event, optional): Event object from Tkinter, if triggered by an event. Defaults to None.

        Raises:
            ValueError: If the order number is invalid or not numeric.
        """
        order_number = order_number_entry.get().strip()

        if validate_order_number(order_number):
            processed_number = process_order_number(order_number)

            order_numbers.append(processed_number)
            order_listbox.insert(tk.END, processed_number)

            order_number_entry.delete(0, tk.END)
            order_number_entry.focus_set()

            logger.info(f"Added order number: {processed_number}")
        else:
            show_error_message(
                "Invalid Input",
                "Order number must be numeric and may include periods (e.g., 123456.00).",
            )

    skid_count = 0
    carpet_count = 0
    box_count = 0

    def add_skid_dimension(event=None):
        """
        Adds a validated skid dimension to the dimensions list and updates the relevant counts.

        Args:
            event (tk.Event, optional): Event object from Tkinter, if triggered by an event. Defaults to None.
        """
        nonlocal skid_count, carpet_count, box_count

        carrier_name = CARRIER_OPTIONS.get(carrier_var.get(), "")

        if carrier_name == "PARCEL PRO":
            show_error_message(
                "Input Restriction",
                "Parcel Pro only accepts individual items. Please enter the total item count in the 'Cartons' box instead.",
            )
            return

        if carrier_name == "KPS":
            processed_dimensions = "N/A"
        else:
            dimension_str = skid_dimension_entry.get().strip()
            processed_dimensions = process_skid_dimensions(dimension_str)

        if processed_dimensions:
            if classification_var.get() == "Carpet":
                processed_dimensions += " (C)"
                carpet_count += 1
            elif classification_var.get() == "Box":
                processed_dimensions += " (B)"
                box_count += 1
            else:
                skid_count += 1

            skid_dimensions.append(processed_dimensions)
            skid_listbox.insert(tk.END, processed_dimensions)
            skid_dimension_entry.delete(0, tk.END)

            update_skid_count()
            logger.info(
                f"Added dimension: {processed_dimensions} | Skid Count: {skid_count}, Carpet Count: {carpet_count}, Box Count: {box_count}"
            )
        else:
            if carrier_name not in ["KPS", "PARCEL PRO"]:
                show_error_message(
                    "Invalid Input",
                    "Please enter a valid dimension format (e.g., 62x45x33).",
                )

    def process_skid_dimensions(dimension_str):
        """
        Validates and processes a skid dimension string.

        If the input matches specific patterns, it formats the string as "LxWxH".

        Args:
            dimension_str (str): Skid dimension string to process.

        Returns:
            str: Processed skid dimensions in "LxWxH" format, or None if validation fails.
        """
        carrier_name = CARRIER_OPTIONS.get(carrier_var.get(), "")

        if carrier_name == "PARCEL PRO":
            return dimension_str

        if re.match(r"^\d{6}$", dimension_str):
            return f"{dimension_str[:2]}x{dimension_str[2:4]}x{dimension_str[4:]}"

        dimensions = re.split(r"\D+", dimension_str.strip())

        if len(dimensions) != 3 or not all(dim.isdigit() for dim in dimensions):
            show_error_message(
                "Invalid Input",
                "Please enter exactly three numeric dimensions (e.g., 62x45x33).",
            )
            return None

        return f"{dimensions[0]}x{dimensions[1]}x{dimensions[2]}"

    def update_skid_count():
        """
        Updates the displayed skid count based on the entered dimensions, excluding carpets and boxes.
        """
        skid_only_count = sum(
            1 for dim in skid_dimensions if "(C)" not in dim and "(B)" not in dim
        )
        skid_count_entry.delete(0, tk.END)
        skid_count_entry.insert(0, skid_only_count)
        logger.info(f"Updated skid count: {skid_only_count}")

    def delete_selected_item():
        """
        Deletes the selected item (order number or skid dimension) from the respective listbox.
        """
        if order_listbox.curselection():
            index = order_listbox.curselection()[0]
            deleted_order = order_numbers[index]
            order_listbox.delete(index)
            del order_numbers[index]
            logger.info(f"Deleted order number: {deleted_order}")
        elif skid_listbox.curselection():
            index = skid_listbox.curselection()[0]
            deleted_dimension = skid_dimensions[index]
            skid_listbox.delete(index)
            del skid_dimensions[index]
            update_skid_count()
            logger.info(f"Deleted skid dimension: {deleted_dimension}")

    def validate_inputs():
        """
        Validates all required user inputs before proceeding with Bill of Lading (BOL) generation.

        Returns:
            bool: True if all inputs are valid; False otherwise.
        """
        carrier_choice = carrier_var.get()

        if not validate_carrier_fields(
            carrier_choice,
            tracking_number_entry.get().strip(),
            quote_number_entry.get().strip(),
            quote_price_entry.get().strip(),
            weight_entry.get().strip(),
            CARRIER_OPTIONS,
        ):
            show_error_message(
                "Invalid Input",
                "Carrier-specific validation failed. Please check your input.",
            )
            return False

        if not validate_skid_count(
            carrier_choice,
            skid_count_entry,
            skid_dimensions,
            CARRIER_OPTIONS,
            show_error_message,
        ):
            return False

        logger.info("Input validation successful.")
        return True

    def select_carrier_and_generate():
        logger.info("Starting BOL generation process.")

        # 1. Validate the basic GUI inputs (order numbers, dimensions, etc.)
        if not validate_inputs():
            return

        # 2. Resolve the carrier name
        carrier = choose_carrier(carrier_var.get(), CARRIER_OPTIONS, show_error_message)
        if not carrier:
            return

        # 3. Fetch the DB record for the first order number
        record = get_order_record(order_numbers, show_error_message)
        if not record:
            return

        # 4. Pull all the other fields into a single dict
        context = collect_ui_inputs(
            order_numbers,
            tracking_number_entry,
            skid_count_entry,
            skid_cartons_entry,
            quote_number_entry,
            quote_price_entry,
            weight_entry,
            skid_listbox,
            selected_date_var,
            inside_var,
            tailgate_var,
            appointment_var,
            two_man_var,
            white_glove_var,
            carrier,
            show_error_message,
        )
        if context is None:
            return
        context["carrier_name"] = carrier

        # 5. Generate PDFs (BOL + labels)
        bol_path = build_and_save_pdfs(
            record, context, output_dir_path, logger.info, show_error_message
        )
        if not bol_path:
            return

        # 6. Write updates back to the database
        update_database_for_orders(
            context["order_numbers"],
            context["tracking_number"],
            carrier,
            context["weight"],
            context["skid_cartons"],
            context["quote_price"],
            logger.info,
        )

        # 7. Notify the user of success
        messagebox.showinfo("Success", f"BOL & labels saved to:\n{bol_path}")

    def edit_selected_item():
        """
        Enables editing of the selected item (order number or skid dimension) in the listbox.
        """
        if order_listbox.curselection():
            index = order_listbox.curselection()[0]
            order_number_entry.delete(0, tk.END)
            order_number_entry.insert(0, order_numbers[index])

            def update_order(event=None):
                new_value = order_number_entry.get().strip()
                if re.match(r"^\d+(\.|-|_)?\d*$", new_value):
                    order_numbers[index] = process_order_number(new_value)
                    order_listbox.delete(index)
                    order_listbox.insert(index, order_numbers[index])
                    order_listbox.selection_clear(0, tk.END)
                    order_listbox.selection_set(index)
                    order_number_entry.delete(0, tk.END)
                    edit_button.config(text="Edit", command=edit_selected_item)
                    order_number_entry.bind("<Return>", add_order_number)
                else:
                    show_error_message(
                        "Invalid Input", "Please enter a valid order number."
                    )

            edit_button.config(text="Update", command=update_order)
            order_number_entry.bind("<Return>", update_order)

        elif skid_listbox.curselection():
            index = skid_listbox.curselection()[0]
            skid_text = skid_dimensions[index]

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
        """
        Clears all user inputs, resets GUI variables, and clears the listboxes.
        """
        order_number_entry.delete(0, tk.END)
        order_listbox.delete(0, tk.END)
        skid_dimension_entry.delete(0, tk.END)
        skid_listbox.delete(0, tk.END)
        tracking_number_entry.delete(0, tk.END)
        weight_entry.delete(0, tk.END)
        skid_cartons_entry.delete(0, tk.END)
        skid_count_entry.delete(0, tk.END)
        skid_count_entry.insert(0, "0")
        quote_price_entry.delete(0, tk.END)
        quote_number_entry.delete(0, tk.END)
        selected_date_var.set(CURRENT_DATE)
        order_numbers.clear()
        skid_dimensions.clear()
        logger.info("Cleared all input fields.")

    frame_left = tk.Frame(root)
    frame_right = tk.Frame(root)
    frame_left.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
    frame_right.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

    order_number_entry = make_labeled_entry(frame_left, "Order Number:")
    order_number_entry.bind("<Return>", add_order_number)

    make_button(frame_left, "Add Order Number", add_order_number)

    order_listbox = make_listbox_section(frame_left, "Order Numbers:", height=30)

    skid_dimension_entry = make_labeled_entry(frame_right, "Dimension (LxWxH):")
    skid_dimension_entry.bind("<Return>", add_skid_dimension)

    make_button(frame_right, "Add Dimension", add_skid_dimension)

    classification_frame = tk.Frame(frame_right)
    classification_frame.pack(pady=5)
    tk.Radiobutton(
        classification_frame, text="Skid", variable=classification_var, value="Skid"
    ).pack(side=tk.LEFT)
    tk.Radiobutton(
        classification_frame, text="Carpet", variable=classification_var, value="Carpet"
    ).pack(side=tk.LEFT)
    tk.Radiobutton(
        classification_frame, text="Box", variable=classification_var, value="Box"
    ).pack(side=tk.LEFT)

    skid_listbox = make_listbox_section(frame_right, "Dimensions:", height=30)

    skid_count_entry = make_labeled_entry(frame_right, "Skid Count:", width=5)
    skid_count_entry.insert(0, "0")

    tk.Label(root, text="Select Carrier:").pack(pady=10)
    for key, value in CARRIER_OPTIONS.items():
        tk.Radiobutton(root, text=value, variable=carrier_var, value=key).pack(
            anchor=tk.W
        )

    tracking_number_entry = make_labeled_entry(root, "Tracking Number:")
    weight_entry = make_labeled_entry(root, "Weight:")
    quote_number_entry = make_labeled_entry(root, "Quote #:")
    skid_cartons_entry = make_labeled_entry(root, "Cartons:")
    quote_price_entry = make_labeled_entry(root, "Quote Price:")

    tk.Label(root, text="Delivery Instructions:").pack(pady=5)

    make_button(root, "Select Shipping Date", open_calendar_popup)

    tk.Label(root, textvariable=selected_date_var).pack(pady=5)

    make_checkbox(root, "Inside Delivery", inside_var)
    make_checkbox(root, "Tailgate Delivery", tailgate_var)
    make_checkbox(root, "Appointment Delivery", appointment_var)
    make_checkbox(root, "2-Man Delivery", two_man_var)
    make_checkbox(root, "White Glove Delivery", white_glove_var)

    make_button(root, "Generate PDF", select_carrier_and_generate)
    make_button(root, "Clear All", clear_contents)

    edit_button = make_button(root, "Edit", edit_selected_item)
    make_button(root, "Delete", delete_selected_item)

    order_number_entry.focus_set()

    root.mainloop()


if __name__ == "__main__":
    main()
