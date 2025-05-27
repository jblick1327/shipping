import os
import fitz
from utils import get_logger, CURRENT_DATE, center_text_x, adjust_font_size

logger = get_logger(__name__)


def generate_shipping_label_on_page(
    doc: fitz.Document,
    carrier_name: str,
    receiver_city: str,
    full_address: str,
    item_label: str,
    tracking_number: str,
    reference_number: str,
    label_suffix: str = "",
) -> None:
    """
    Adds a single shipping‐label page to the given PDF document.

    Args:
        doc: the fitz.Document to append the page to.
        carrier_name: e.g. "UPS", "Purolator".
        receiver_city: city or province string.
        full_address: multiline address for the receiver.
        item_label: main label text (e.g. "1/5", "3C/4C", "12 PCES.").
        tracking_number: the shipment’s tracking ID.
        reference_number: invoice or order reference.
        label_suffix: optional secondary label (e.g. "2C/4C").
    """
    page = doc.new_page(width=612, height=792)  # 8.5×11 portrait

    large_font = 60
    small_font = 16
    city_fontsize = adjust_font_size(page, receiver_city, 540, large_font)

    # Carrier name header
    x = center_text_x(page, carrier_name.strip(), large_font)
    page.insert_text(
        (x, 72), carrier_name.strip(), fontsize=large_font, fontname="hebo"
    )
    page.draw_line((92, 80), (520, 80), width=1)

    # Receiver city
    x = center_text_x(page, receiver_city.strip(), city_fontsize)
    page.insert_text(
        (x, 140), receiver_city.strip(), fontsize=city_fontsize, fontname="hebo"
    )
    page.draw_line((72, 160), (540, 160), width=3)

    # Sender & receiver addresses side by side
    sender_address = (
        "LOUISE KOOL & GALT\n" "2123 MCCOWAN ROAD\n" "SCARBOROUGH, ON.\n" "M1S 3Y6"
    )
    sender_lines = sender_address.split("\n")
    receiver_lines = full_address.split("\n")

    sender_y, receiver_y = 190, 190
    for line in sender_lines:
        x = center_text_x(page, line, small_font, part=1, total_parts=2)
        page.insert_text((x, sender_y), line, fontsize=small_font, fontname="helv")
        sender_y += 20

    for line in receiver_lines:
        x = center_text_x(page, line, small_font, part=2, total_parts=2)
        page.insert_text((x, receiver_y), line, fontsize=small_font, fontname="helv")
        receiver_y += 20

    # Main item label (e.g. "1/5" or "12 PCES.")
    bottom_line = 300
    x = center_text_x(page, item_label, large_font)
    page.insert_text((x, bottom_line), item_label, fontsize=large_font, fontname="tibo")

    # Optional suffix (e.g. "2C/4C")
    if label_suffix:
        small_y = bottom_line + 40
        x = center_text_x(page, label_suffix, small_font)
        page.insert_text(
            (x, small_y), label_suffix, fontsize=small_font, fontname="tibo"
        )

    # Date & tracking (side by side or centered)
    track_y = (small_y + 40) if label_suffix else (bottom_line + 40)
    if tracking_number and tracking_number.strip() != reference_number.strip():
        track_text = f"Tracking # {tracking_number.strip()}"
        x = center_text_x(page, track_text, small_font, part=2, total_parts=2)
        page.insert_text((x, track_y), track_text, fontsize=small_font, fontname="helv")

        date_x = center_text_x(page, CURRENT_DATE, small_font, part=1, total_parts=2)
        page.insert_text(
            (date_x, track_y), CURRENT_DATE, fontsize=small_font, fontname="helv"
        )
    else:
        x = center_text_x(page, CURRENT_DATE, small_font)
        page.insert_text(
            (x, track_y), CURRENT_DATE, fontsize=small_font, fontname="helv"
        )

    # Reference number at bottom
    ref_text = f"Reference #: {reference_number.strip()}"
    ref_x = center_text_x(page, ref_text, small_font)
    page.insert_text(
        (ref_x, track_y + 30), ref_text, fontsize=small_font, fontname="helv"
    )


def generate_labels(
    output_folder: str,
    result: dict,
    carrier_name: str,
    tracking_number: str,
    skid_count: int,
    carpet_count: int,
    box_count: int,
    skid_cartons: int,
    order_numbers: list[str],
    quote_number: str,
    quote_price: str,
    weight: str,
    skid_dimensions: list[str],
) -> str:
    """
    Builds and saves a multi‐page label PDF for the given shipment.

    Args:
        output_folder: directory to save the label PDF.
        result: DB record dictionary (must include 'SSD_SHIPMENT_ID' and address fields).
        carrier_name, tracking_number, counts, etc.: as passed into generate_bol().
    Returns:
        The full path to the saved label PDF.
    """
    shipment_id    = result["SSD_SHIPMENT_ID"].strip()
    clean_carrier  = carrier_name.strip().replace(" ", "")
    clean_ship_id  = shipment_id.replace(" ", "")
    label_path     = os.path.join(
        output_folder,
        f"{clean_carrier}_{clean_ship_id}_Label.pdf"
    )

    doc = fitz.open()
    full_addr = (
        f"{result['SSD_SHIP_TO']}\n"
        f"{result['SSD_SHIP_TO_2']}\n"
        f"{result['SSD_SHIP_TO_4']}\n"
        f"{result['SSD_SHIP_TO_POSTAL']}"
    )

    if carrier_name == "PARCEL PRO":
        # Single‐page case
        generate_shipping_label_on_page(
            doc,
            carrier_name,
            result["SSD_SHIP_TO_4"],
            full_addr,
            f"{skid_cartons} PCES.",
            tracking_number,
            shipment_id,
        )
    else:
        total = skid_count + carpet_count + box_count
        counter = 1

        # Skids
        for _ in range(skid_count):
            generate_shipping_label_on_page(
                doc,
                carrier_name,
                result["SSD_SHIP_TO_4"],
                full_addr,
                f"{counter}/{total}",
                tracking_number,
                shipment_id,
            )
            counter += 1

        # Carpets
        for i in range(1, carpet_count + 1):
            suffix = f"{i}C/{carpet_count}C"
            generate_shipping_label_on_page(
                doc,
                carrier_name,
                result["SSD_SHIP_TO_4"],
                full_addr,
                f"{counter}/{total}",
                tracking_number,
                shipment_id,
                suffix,
            )
            counter += 1

        # Boxes
        for i in range(1, box_count + 1):
            suffix = f"{i}B/{box_count}B"
            generate_shipping_label_on_page(
                doc,
                carrier_name,
                result["SSD_SHIP_TO_4"],
                full_addr,
                f"{counter}/{total}",
                tracking_number,
                shipment_id,
                suffix,
            )
            counter += 1

    doc.save(label_path)
    doc.close()
    logger.info(f"Shipping labels saved to: {label_path}")
    return label_path
