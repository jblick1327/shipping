import fitz  # PyMuPDF
import os
import configparser
from utils import log_error, log_info, get_full_path, ensure_directory_exists, ensure_directory_exists_with_date, center_text_x, adjust_font_size, CURRENT_DATE  # Include center_text_x and adjust_font_size
from helpers import clean_text_refined, format_city_province


# Load config.ini for template paths and directories
config = configparser.ConfigParser()
config.read('config.ini')

# Fetch paths from config.ini
TEMPLATE_PDF = config['paths']['template_pdf']  # Path to PDF template from config
LOG_FILE_PATH = config['logging']['log_file']

def get_full_path(relative_path):
    """
    Converts a relative path into an absolute path based on the current working directory.
    This ensures cross-platform compatibility.
    """
    return os.path.abspath(os.path.join(os.getcwd(), relative_path))


# Convert relative paths to absolute paths
template_pdf_path = get_full_path(TEMPLATE_PDF)  # Full path to the template PDF

# Ensure output folder exists and create if necessary
def ensure_directory_exists(output_folder):
    """
    Ensure that the output directory exists. If it doesn't, create it.
    """
    os.makedirs(output_folder, exist_ok=True)
    log_info(f"Ensured that output directory exists: {output_folder}")


def fill_pdf(input_pdf_path, output_pdf_path, data_map):
    """
    Fill a PDF form with the provided data, saving the filled PDF to a specified output path.
    """
    try:
        log_info(f"Attempting to open template PDF: {input_pdf_path}")
        doc = fitz.open(input_pdf_path)
        
        log_info("Starting to fill the PDF with data")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            for field in page.widgets():
                if field.field_name in data_map:
                    # Convert all values to string to avoid type issues
                    value = str(data_map[field.field_name]) if data_map[field.field_name] is not None else ''
                    log_info(f"Filling field: {field.field_name} with value: '{value}'")

                    # Check if the field value is valid before setting it
                    if isinstance(value, str):
                        field.field_value = value
                        field.update()
                    else:
                        log_error(f"Invalid field value type for {field.field_name}: Expected str, got {type(value)}")

        log_info(f"Attempting to save filled PDF to: {output_pdf_path}")
        doc.save(output_pdf_path)
        doc.close()

        log_info(f"PDF successfully saved at: {output_pdf_path}")
        return True

    except Exception as e:
        log_error(f"Failed to generate PDF: {e}")
        return False
    
def populate_skid_dimensions(data_map, skid_dimensions):
    dim_groups = [skid_dimensions[i:i+3] for i in range(0, len(skid_dimensions), 3)]
    desc_fields = ['Desc_2', 'Desc_3', 'Desc_4', 'Desc_5', 'Desc_6', 'Desc_7', 'Desc_8']

    for i, group in enumerate(dim_groups):
        data_map[desc_fields[i]] = ', '.join(group)


def prepare_data_map(result, skid_count, carpet_count, box_count, skid_cartons, order_numbers, carrier_name, quote_number, quote_price, tracking_number, weight, skid_dimensions):
    """
    Prepare the data map for filling the PDF based on user inputs and order data.
    """
    # Base fields for BOL population
    data_map = {
        'BOLnum': result['SSD_SHIPMENT_ID'],
        'ToName': result['SSD_SHIP_TO'] or 'Unknown',
        'ToAddress': result['SSD_SHIP_TO_2'] or 'Unknown Address',
        'ToCityStateZip': f"{(result['SSD_SHIP_TO_4'] or 'Unknown City').strip()}. {(result['SSD_SHIP_TO_POSTAL'] or 'Unknown Postal Code').strip()}",
        'BillInstructions': clean_text_refined(result['SSD_SHIP_TO_3'])[0],  # Handle ATTN field
        'CarrierName': carrier_name,
        'Date': CURRENT_DATE,
        'HU_QTY_1': str(skid_count) if skid_count > 0 else '',
        'HU_QTY_2': str(carpet_count) if carpet_count > 0 else '',
        'HU_QTY_3': str(box_count) if box_count > 0 else '',
        'Pkg_QTY_1': str(skid_cartons),
        'PRO': tracking_number,
        'WT_1': f"{weight} LBS." if weight else ""  # Weight field passed from the GUI
    }

    # Handle multiple order numbers with commas
    if order_numbers:
        data_map['OrderNum1'] = order_numbers[0]
        if len(order_numbers) > 1:
            data_map['OrderNum1'] += f", {order_numbers[1]}"
        
        # Add to subsequent order number fields
        order_num_fields = ['OrderNum2', 'OrderNum3', 'OrderNum4', 'OrderNum5', 'OrderNum6']
        for i, field in enumerate(order_num_fields):
            first_index = i * 2 + 2
            second_index = first_index + 1
            
            if len(order_numbers) > first_index:
                if len(order_numbers) > second_index:
                    data_map[field] = f"{order_numbers[first_index]}, {order_numbers[second_index]}"
                else:
                    data_map[field] = order_numbers[first_index]

    # Carrier-specific fields
    if carrier_name == 'FF':
        data_map['FromSIDNum'] = '402140'
        data_map['OrderNum7'] = f"Quote #: {quote_number}" if quote_number else "Quote #: QN ID"
    elif carrier_name == 'NFF':
        data_map['FromSIDNum'] = 'LOU006'
        data_map['OrderNum7'] = f"Quote #: {quote_number}" if quote_number else "Quote #: "
    
    # Quote Price for specific carriers
    if carrier_name in ['FF', 'NFF', 'FF LOGISTICS', 'CRR']:
        data_map['OrderNum8'] = f"${quote_price}" if quote_price else "$"

    # Constants (hardcoded values)
    constants = {
        'FromName': 'LOUISE KOOL & GALT',
        'FromAddr': '2123 MCCOWAN ROAD',
        'FromCityStateZip': 'SCARBOROUGH, ON. M1S 3Y6',
        'AddInfo8': 'INSIDE DELIVERY & TAILGATE DELIVERY',
        'Prepaid': '     X',
        'Page_ttl': '     1',
        'Desc_1': 'CHILDCARE MATERIALS/FURNITURE',
        'Pkg_Type_1': 'PCES.'
    }
    data_map.update(constants)

    # Skid dimensions population into description fields
    populate_skid_dimensions(data_map, skid_dimensions)

    # Add "SKIDS" to HU_Type_1 if it's applicable
    if skid_count > 0:
        data_map['HU_Type_1'] = "SKIDS"
    else:
        data_map['HU_Type_1'] = ""  # Ensure it's cleared if no skids

    # Handle carpets and boxes
    if carpet_count > 0:
        data_map['HU_Type_2'] = "CRPTS."  # Carpets
    if box_count > 0:
        data_map['HU_Type_3'] = "BOXES"  # Boxes

    return data_map

def generate_labels(doc, result, carrier_name, skid_count, carpet_count, box_count, tracking_number, output_folder_with_date):
    """
    Generate and add shipping labels for skids, carpets, or boxes to the PDF document.
    
    Args:
        doc (fitz.Document): The PDF document to which the labels will be added.
        result (dict): Data fetched from the database.
        carrier_name (str): The name of the carrier.
        skid_count (int): Number of skids.
        carpet_count (int): Number of carpets.
        box_count (int): Number of boxes.
        tracking_number (str): The tracking number for the shipment.
        output_folder_with_date (str): The folder where the labels will be saved.
    """
    total_items = skid_count + carpet_count + box_count  # Total number of items to label

    formatted_city_province = format_city_province(result['SSD_SHIP_TO_4'])
    full_address = f"{result['SSD_SHIP_TO']}\n{result['SSD_SHIP_TO_2']}\n{formatted_city_province}\n{result['SSD_SHIP_TO_POSTAL']}"


    # Call the label generation function
    generate_shipping_label_on_page(
        doc, 
        carrier_name, 
        result['SSD_SHIP_TO_4'],  # City or equivalent field
        full_address,  # The full address string formatted as needed
        f"{current_item}/{total_items}", 
        tracking_number, 
        reference_number
)


    # Generate labels for each item
    current_item = 1
    reference_number = result['SSD_SHIPMENT_ID'].strip()  # Use the shipment ID as the reference number

    # Generate labels for skids
    for _ in range(skid_count):
        generate_shipping_label_on_page(
            doc,
            carrier_name,
            result['SSD_SHIP_TO_4'],  # Receiver city
            result['SSD_SHIP_TO'],     # Full address
            f"{current_item}/{total_items}",  # Item label (e.g., 1/4)
            tracking_number,
            reference_number
        )
        current_item += 1

    # Generate labels for carpets
    for i in range(1, carpet_count + 1):
        label_suffix = f"{i}C/{carpet_count}C"  # Carpets are labeled with "C"
        generate_shipping_label_on_page(
            doc,
            carrier_name,
            result['SSD_SHIP_TO_4'],  # Receiver city
            result['SSD_SHIP_TO'],     # Full address
            f"{current_item}/{total_items}",  # Item label (e.g., 1/4)
            tracking_number,
            reference_number,
            label_suffix  # Carpet label suffix
        )
        current_item += 1

    # Generate labels for boxes
    for i in range(1, box_count + 1):
        label_suffix = f"{i}B/{box_count}B"  # Boxes are labeled with "B"
        generate_shipping_label_on_page(
            doc,
            carrier_name,
            result['SSD_SHIP_TO_4'],  # Receiver city
            result['SSD_SHIP_TO'],     # Full address
            f"{current_item}/{total_items}",  # Item label (e.g., 1/4)
            tracking_number,
            reference_number,
            label_suffix  # Box label suffix
        )
        current_item += 1

    # Save the label PDF to the specified folder
    label_output_pdf = os.path.join(output_folder_with_date, f"{carrier_name}_shipping_labels.pdf")
    doc.save(label_output_pdf)
    doc.close()

    # Log the success
    log_info(f"Shipping labels successfully generated at: {label_output_pdf}")

    # Auto-open the labels PDF
    os.startfile(label_output_pdf)  # Open the labels PDF automatically



def generate_shipping_label_on_page(doc, carrier_name, receiver_city, full_address, item_label, tracking_number, reference_number, label_suffix=""):
    """
    Add a shipping label for skids, carpets, or boxes to an existing PDF document.
    
    Args:
        doc (fitz.Document): The PDF document to which the shipping label is added.
        carrier_name (str): The name of the carrier.
        receiver_city (str): The city of the receiver.
        full_address (str): The full address of the receiver.
        item_label (str): The current item label (e.g., '1/4', '2/4').
        tracking_number (str): The tracking number to be displayed.
        reference_number (str): The reference number to display (e.g., SSD_SHIPMENT_ID or order_number).
        label_suffix (str): The label suffix (e.g., '1C/1C' for carpets).
    """
    # Create a new page in the PDF
    page = doc.new_page(width=612, height=792)  # 8.5x11 portrait size in points

    large_font = 60
    small_font = 16
    city_fontsize = adjust_font_size(page, receiver_city, 540, large_font)

    # Draw the carrier name and receiver city in large font
    x = center_text_x(page, carrier_name.strip(), large_font)
    page.insert_text((x, 72), carrier_name.strip(), fontsize=large_font, fontname="hebo", fill=(0, 0, 0))

    page.draw_line((92, 80), (520, 80), width=1)

    x = center_text_x(page, receiver_city.strip(), city_fontsize)
    page.insert_text((x, 140), receiver_city.strip(), fontsize=city_fontsize, fontname="hebo", fill=(0, 0, 0))

    # Draw a dividing line
    page.draw_line((72, 160), (540, 160), width=3)

    # Split the full address into individual lines
    sender_address = "LOUISE KOOL & GALT\n2123 MCCOWAN ROAD\nSCARBOROUGH, ON.\nM1S 3Y6"
    sender_lines = sender_address.split("\n")
    receiver_lines = [line.strip() for line in full_address.split("\n")]

    sender_y = 190
    receiver_y = 190

    # Draw the sender address on the left
    for line in sender_lines:
        x = center_text_x(page, line.strip(), small_font, part=1, total_parts=2)
        page.insert_text((x, sender_y), line.strip(), fontsize=small_font, fontname="helv", fill=(0, 0, 0))
        sender_y += 20

    # Draw the receiver address on the right
    for line in receiver_lines:
        x = center_text_x(page, line.strip(), small_font, part=2, total_parts=2)
        page.insert_text((x, receiver_y), line.strip(), fontsize=small_font, fontname="helv", fill=(0, 0, 0))
        receiver_y += 20

    # Draw item count (e.g., 4/4) in large font
    bottom_line = 300
    x = center_text_x(page, f"{item_label}".strip(), large_font)
    page.insert_text((x, bottom_line), f"{item_label}".strip(), fontsize=large_font, fontname="tibo", fill=(0, 0, 0))

    # If there is a label suffix (e.g., 1C/1C for carpets), draw it in smaller font directly below the main item count
    if label_suffix:
        small_font_y = bottom_line + 40  # Slightly below the main label
        x = center_text_x(page, f"{label_suffix}".strip(), small_font)
        page.insert_text((x, small_font_y), f"{label_suffix}".strip(), fontsize=small_font, fontname="tibo", fill=(0, 0, 0))

    # Adjust the bottom line for the tracking number and date placement
    tracking_bottom_line = small_font_y + 40 if label_suffix else bottom_line + 40
    if tracking_number:
        tracking_text = f"Tracking # {tracking_number.strip()}"
        x = center_text_x(page, tracking_text, small_font, part=2, total_parts=2)
        page.insert_text((x, tracking_bottom_line), tracking_text, fontsize=small_font, fontname="helv", fill=(0, 0, 0))

        # Insert the current date (using CURRENT_DATE constant or variable)
        x = center_text_x(page, CURRENT_DATE.strip(), small_font, part=1, total_parts=2)
        page.insert_text((x, tracking_bottom_line), CURRENT_DATE.strip(), fontsize=small_font, fontname="helv", fill=(0, 0, 0))
    else:
        # If no tracking number, just insert the date
        x = center_text_x(page, CURRENT_DATE.strip(), small_font)
        page.insert_text((x, tracking_bottom_line), CURRENT_DATE.strip(), fontsize=small_font, fontname="helv", fill=(0, 0, 0))

    # Adjust the position of the reference number relative to the bottom line
    reference_text = f"Reference #: {reference_number.strip()}"
    reference_x = center_text_x(page, reference_text, small_font)
    page.insert_text((reference_x, tracking_bottom_line + 30), reference_text, fontsize=small_font, fontname="helv", fill=(0, 0, 0))


def generate_bol(result, carrier_name, tracking_number, skid_count, carpet_count, box_count, skid_cartons, output_folder, skid_dimensions, order_numbers, quote_number, quote_price, weight):
    # Safely generate a filename for the output PDF
    ssd_shipment_id = result['SSD_SHIPMENT_ID'].strip()  # Strip any excess whitespace
    safe_order_number = ssd_shipment_id.replace('.', '_').strip()  # Replace dots in shipment ID with underscores and strip
    carrier_name_stripped = "_".join(carrier_name.split()).strip()  # Remove extra spaces in carrier name
    output_pdf_filled = os.path.join(output_folder, f"{carrier_name_stripped}_{safe_order_number}_BOL.pdf").strip()  # Remove any excess spaces in final path
    output_pdf_filled = os.path.normpath(output_pdf_filled.strip())  # Normalize path and remove excess whitespace

    # Prepare the data map (include skid_dimensions and order_numbers as an argument)
    data_map = prepare_data_map(
        result, skid_count, carpet_count, box_count, skid_cartons, order_numbers, 
        carrier_name, quote_number, quote_price, tracking_number, weight, skid_dimensions)

    # Call the fill_pdf function to fill the template PDF with data
    if fill_pdf(template_pdf_path, output_pdf_filled, data_map):
        log_info(f"BOL successfully generated at: {output_pdf_filled}")
        
        # Generate shipping label for skids, carpets, and boxes
        doc = fitz.open()  # Create a new document
        output_pdf_label = os.path.join(output_folder, f"{carrier_name_stripped}_{ssd_shipment_id}_Label.pdf")

        # Full receiver address for the label
        formatted_city_province = format_city_province(result['SSD_SHIP_TO_4'])
        full_address = f"{result['SSD_SHIP_TO']}\n{result['SSD_SHIP_TO_2']}\n{formatted_city_province}\n{result['SSD_SHIP_TO_POSTAL']}"

        # Generate labels for all items (skids, carpets, boxes)
        total_items = skid_count + carpet_count + box_count
        current_item = 1

        # The reference number is the shipment ID, strip any extra whitespace
        reference_number = result['SSD_SHIPMENT_ID'].strip()

        # Generate labels for skids
        for _ in range(skid_count):
            generate_shipping_label_on_page(doc, carrier_name, result['SSD_SHIP_TO_4'], full_address, f"{current_item}/{total_items}", tracking_number, reference_number)
            current_item += 1

        # Generate labels for carpets
        for i in range(1, carpet_count + 1):
            label_suffix = f"{i}C/{carpet_count}C"
            generate_shipping_label_on_page(doc, carrier_name, result['SSD_SHIP_TO_4'], full_address, f"{current_item}/{total_items}", tracking_number, reference_number, label_suffix)
            current_item += 1

        # Generate labels for boxes
        for i in range(1, box_count + 1):
            label_suffix = f"{i}B/{box_count}B"
            generate_shipping_label_on_page(doc, carrier_name, result['SSD_SHIP_TO_4'], full_address, f"{current_item}/{total_items}", tracking_number, reference_number, label_suffix)
            current_item += 1

        # Save and open the label PDF
        doc.save(output_pdf_label)
        log_info(f"Shipping label successfully generated at: {output_pdf_label}")

        # Automatically open the BOL PDF
        os.startfile(output_pdf_filled)

        # Automatically open the Label PDF
        os.startfile(output_pdf_label)

        return output_pdf_filled
    else:
        log_error("Failed to generate BOL PDF.")
        return None

