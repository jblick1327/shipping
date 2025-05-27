import fitz
from utils import get_logger, get_full_path, load_config

logger = get_logger(__name__)
config = load_config()
template_pdf_path = get_full_path(config["paths"]["template_pdf"])


def fill_pdf(input_pdf_path: str, output_pdf_path: str, data_map: dict) -> bool:
    """
    Fills a PDF form with data from a dictionary.
    """
    try:
        doc = fitz.open(input_pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            for widget in page.widgets():
                name = widget.field_name
                if name in data_map:
                    value = str(data_map[name]) or ""
                    widget.field_value = value
                    widget.update()
        doc.save(output_pdf_path)
        doc.close()
        logger.info(f"Filled PDF saved to: {output_pdf_path}")
        return True
    except Exception as e:
        logger.error(f"fill_pdf error: {e}")
        return False
