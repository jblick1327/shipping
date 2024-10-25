
---

# Project Documentation

## Database Module (`database.py`)
### Overview
The `database.py` module facilitates order data retrieval and shipping updates in two modes: production (ODBC) and testing (CSV). It handles credential checks, data access based on environment, and logs activity and errors for effective debugging.

### Key Features
- **Dual-Mode Operation**: Selects between ODBC and CSV data retrieval based on `DB_MODE` (production or mock).
- **Credential Verification**: Checks for ODBC credentials in production mode and raises an error if missing.
- **Comprehensive Error Logging**: Logs connectivity and data retrieval issues to aid in troubleshooting.

### Core Functions
- **`fetch_order_data(order_number)`**: Directs data requests to `mock_get_order_data` or `get_odbc_order_data` based on mode.
- **`update_shipping_data(...)`**: Routes updates to shipping data functions (`mock_update_shipping_data` or `update_odbc_shipping_data`).

---

## Graphical User Interface Module (`gui.py`)
### Overview
Built with Tkinter, the `gui.py` module provides an interactive interface to manage order and shipping data, handle carrier-based validations, and automate BOL generation and database updates.

### Key Features
- **Carrier-Specific Validation**: Applies unique validation rules for each carrier, with restricted inputs for some (e.g., `Parcel Pro` only allows item counts).
- **Order and Dimension Management**: Allows adding, editing, and deleting orders and dimensions and validates user inputs.
- **Automated BOL Generation**: Fetches order data, validates inputs, and generates a BOL PDF and labels.

### Core Functions
- **Order and Dimension Handling**: Functions like `add_order_number`, `add_skid_dimension`, and `delete_selected_item` manage list entries and validations.
- **PDF Generation and Carrier Selection**: `select_carrier_and_generate` validates inputs, selects data sources, and generates BOL PDFs.
- **Date Selection and Error Handling**: Includes a date picker and error display to assist user input.

---

## Helper Module (`helpers.py`)
### Overview
This module standardizes input validation and formatting, supporting phone number normalization, city/province abbreviations, and custom prompts.

### Key Features
- **Data Formatting**: Functions like `format_city_province` and `clean_phone_number` ensure consistent data presentation.
- **Customizable Prompts**: `ask_attention_substitute` prompts for missing “Attention to” data based on available inputs.
- **Carrier-Specific Validation**: Validates skid counts and carrier-based field requirements with functions like `validate_skid_count`.

### Core Functions
- **Input Validation**: Validates fields based on carrier type and standardizes user input with functions like `validate_carrier_fields` and `get_delivery_instructions`.
- **Data Formatting**: `process_order_number`, `clean_text_refined`, and `format_city_province` ensure consistency in formatting.

---

## PDF Generation Module (`pdf_generator.py`)
### Overview
The `pdf_generator.py` module creates BOL and shipping label PDFs with flexible field population and formatted layout for clear, organized documents.

### Key Features
- **Template-Based Population**: Maps structured data to PDF templates and manages font sizes and alignment for readability.
- **Automated File Organization**: Saves files in a date-based folder structure for quick retrieval.
- **Dynamic Label and BOL Generation**: Creates multiple labels and BOLs, formatted with carrier names, tracking info, and standardized text layouts.

### Core Functions
- **PDF Population and Label Creation**: `fill_pdf` and `generate_shipping_label_on_page` populate BOL and label fields with customized data.
- **Data Preparation for PDFs**: `prepare_data_map` structures user inputs and maps them to relevant PDF fields.
- **Saving PDFs**: `generate_bol` coordinates BOL and label generation, saving outputs in organized folders.

---

## Utilities Module (`utils.py`)
### Overview
The `utils.py` module contains foundational utilities for logging, path handling, and text adjustments, supporting consistent file organization, error tracking, and layout for PDFs.

### Key Features
- **Date-Based Directory Structure**: Organizes files by month and day (e.g., `October 2024/October 26`) to simplify navigation.
- **Centralized Logging**: `log_info` and `log_error` provide a unified logging system for all modules.
- **Text Layout for PDFs**: Functions like `center_text_x` and `adjust_font_size` adjust text alignment and size for optimized presentation in PDF fields.

### Core Functions
- **Directory and Path Handling**: `get_full_path` and `ensure_directory_exists_with_date` manage path conversions and folder creation.
- **Validation and Text Utilities**: Functions like `validate_order_number` and `validate_alphanumeric` standardize user input across modules.

---
