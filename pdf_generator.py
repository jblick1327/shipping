from utils import get_logger
from build_data_map import prepare_data_map
from fill_pdf import fill_pdf, template_pdf_path
from label_generator import generate_labels
import os

logger = get_logger(__name__)


def generate_bol(
    result: dict,
    carrier_name: str,
    tracking_number: str,
    skid_count: int,
    carpet_count: int,
    box_count: int,
    skid_cartons: int,
    output_folder: str,
    skid_dimensions: list[str],
    order_numbers: list[str],
    quote_number: str,
    quote_price: str,
    weight: str,
    add_info_7: str,
    add_info_8: str,
) -> str | None:
    """
    High-level Bill of Lading process: fill form, generate labels.
    """
    # 1) Prepare the map
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
        add_info_7,
        add_info_8,
    )

    # 2) Fill & save the BOL PDF
    bol_path = os.path.join(
        output_folder,
        f"{carrier_name.strip().replace(' ', '')}_"
        f"{result['SSD_SHIPMENT_ID'].strip().replace(' ', '')}_BOL.pdf"
    )
    if not fill_pdf(template_pdf_path, bol_path, data_map):
        return None

    # 3) Generate & save labels
    label_path = generate_labels(
        output_folder,
        result,
        carrier_name,
        tracking_number,
        skid_count,
        carpet_count,
        box_count,
        skid_cartons,
        order_numbers,
        quote_number,
        quote_price,
        weight,
        skid_dimensions,
    )

    # 4) Optionally open files
    os.startfile(bol_path)
    os.startfile(label_path)

    return bol_path
