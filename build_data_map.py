from utils import clean_text_refined, CURRENT_DATE


def prepare_data_map(
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
):
    """
    Prepares a data map for populating the PDF with shipping information.

    Args:
        result (dict): Order data fetched from the database.
        ... (several other args describe individual data points)

    Returns:
        dict: Fully prepared data map for PDF fields.
    """
    data_map = {
        "BOLnum": result["SSD_SHIPMENT_ID"],
        "ToName": result["SSD_SHIP_TO"] or "Unknown",
        "ToAddress": result["SSD_SHIP_TO_2"] or "Unknown Address",
        "ToCityStateZip": (
            f"{(result['SSD_SHIP_TO_4'] or 'Unknown City').strip()}."
            f" {(result['SSD_SHIP_TO_POSTAL'] or 'Unknown Postal Code').strip()}"
        ),
        "BillInstructions": clean_text_refined(result["SSD_SHIP_TO_3"])[0],
        "CarrierName": carrier_name,
        "Date": CURRENT_DATE,
        "HU_QTY_1": str(skid_count) if skid_count > 0 else "",
        "HU_QTY_2": str(carpet_count) if carpet_count > 0 else "",
        "HU_QTY_3": str(box_count) if box_count > 0 else "",
        "Pkg_QTY_1": str(skid_cartons - carpet_count - box_count),
        "PRO": tracking_number,
        "WT_1": f"{weight} LBS." if weight else "",
        "AddInfo7": add_info_7,
        "AddInfo8": add_info_8,
    }

    if order_numbers:
        data_map["OrderNum1"] = order_numbers[0]
        if len(order_numbers) > 1:
            data_map["OrderNum1"] += f", {order_numbers[1]}"

        order_num_fields = [
            "OrderNum2",
            "OrderNum3",
            "OrderNum4",
            "OrderNum5",
            "OrderNum6",
        ]
        for i, field in enumerate(order_num_fields):
            first_index = i * 2 + 2
            second_index = first_index + 1

            if len(order_numbers) > first_index:
                if len(order_numbers) > second_index:
                    data_map[field] = (
                        f"{order_numbers[first_index]}, {order_numbers[second_index]}"
                    )
                else:
                    data_map[field] = order_numbers[first_index]

    if carrier_name == "FF":
        data_map["FromSIDNum"] = "402140"
        data_map["OrderNum7"] = (
            f"Quote #: {quote_number}" if quote_number else "Quote #: QN ID"
        )
    elif carrier_name == "NFF":
        data_map["FromSIDNum"] = "LOU006"
        data_map["OrderNum7"] = (
            f"Quote #: {quote_number}" if quote_number else "Quote #: "
        )

    if carrier_name in ["FF", "NFF", "FF LOGISTICS", "CRR"]:
        data_map["OrderNum8"] = f"${quote_price}" if quote_price else "$"

    # Constants (hardcoded values)
    constants = {
        "FromName": "LOUISE KOOL & GALT",
        "FromAddr": "2123 MCCOWAN ROAD",
        "FromCityStateZip": "SCARBOROUGH, ON. M1S 3Y6",
        "Prepaid": "     X",
        "Page_ttl": "     1",
        "Desc_1": "CHILDCARE MATERIALS/FURNITURE",
        "Pkg_Type_1": "PCES.",
    }
    data_map.update(constants)

    populate_skid_dimensions(data_map, skid_dimensions)

    if skid_count > 0:
        data_map["HU_Type_1"] = "SKIDS"
    else:
        data_map["HU_Type_1"] = ""

    if carpet_count > 0:
        data_map["HU_Type_2"] = "CRPTS."
    if box_count > 0:
        data_map["HU_Type_3"] = "BOXES"

    return data_map


def populate_skid_dimensions(data_map, skid_dimensions):
    """
    Populates description fields in the data map with skid dimensions.

    Args:
        data_map (dict): Data map for the PDF fields.
        skid_dimensions (list): List of skid dimensions to include.

    Modifies:
        data_map (dict): Updates description fields with skid dimensions.
    """
    dim_groups = [skid_dimensions[i:i + 3] for i in range(0, len(skid_dimensions), 3)]
    desc_fields = ["Desc_2", "Desc_3", "Desc_4", "Desc_5", "Desc_6", "Desc_7", "Desc_8"]

    for i, group in enumerate(dim_groups):
        # Filter out any dimension starting with "N/A"
        filtered_group = [dim for dim in group if not dim.startswith("N/A")]

        if filtered_group:
            data_map[desc_fields[i]] = ", ".join(filtered_group)
