# Project Documentation

## **Database Module (`database.py`)**

### Overview
The `database.py` module handles retrieval and updating of order and shipping data in two modes: **production (ODBC)** and **testing (mock CSV)**, controlled by the `DB_MODE` setting. This dual-mode approach supports both development and live environments.

### Key Features
- **Dual-Mode Operation**: In production, the module uses ODBC to connect to a database (`get_odbc_order_data` and `update_odbc_shipping_data`). In testing, it fetches data from a CSV (`mock_get_order_data`) and logs updates without modifying data (`mock_update_shipping_data`).
- **Credential Verification**: Ensures that ODBC credentials are present before connecting in production mode, logging an error if credentials are missing.
- **Error Handling**: Logs errors and connection issues, making troubleshooting straightforward.

### Core Functions
- **`fetch_order_data(order_number)`**  
  Routes requests to either `mock_get_order_data` or `get_odbc_order_data` depending on `DB_MODE`.
- **`update_shipping_data(...)`**  
  Manages updates to shipping data in the database, directing to either `mock_update_shipping_data` or `update_odbc_shipping_data` based on mode.

---

## **Graphical User Interface Module (`gui.py`)**

### Overview
The `gui.py` module, built with **Tkinter**, provides an interface for managing order and shipping data. It adapts based on carrier selections and enforces custom input validations, making it both interactive and intuitive.

### Key Features
- **Carrier-Specific Validation**: Enforces unique rules for each carrier (e.g., “Skid” classification disabled for PARCEL PRO) and uses dynamically populated fields for order and dimension data.
- **Interactive Feedback**: Popups guide users through inputs with error messages and a calendar for date selection.
- **Order and Dimension Management**: Functions for adding, editing, deleting, and validating entries, including popups for error messages, streamline the user experience.

### Core Functions
- **Order Number and Dimension Handling**  
  Functions like `add_order_number`, `add_skid_dimension`, and `delete_selected_item` handle adding, validating, and deleting list items.
- **Data Validation and PDF Generation**  
  `select_carrier_and_generate` validates all inputs, fetches data, and triggers PDF generation through `pdf_generator.generate_bol`.
- **Date Selection and Error Handling**  
  `open_calendar_popup` opens a date picker, and `show_error_message` displays validation errors, improving user interaction.

---

## **Helper Module (`helpers.py`)**

### Overview
This module standardizes data validation and formatting, simplifying the process of managing inputs such as phone numbers, city/province names, and “Attention to” details.

### Key Features
- **Data Formatting**: `format_city_province` converts full province names to abbreviations, and `clean_phone_number` normalizes phone formats.
- **Customizable User Prompts**: `ask_attention_substitute` prompts users for missing “Attention to” data, offering possible alternatives based on available fields.
- **Carrier-Specific Validation**: Functions like `validate_skid_count` enforce rules for skid counts based on carrier choice, and `validate_carrier_fields` applies checks specific to each carrier.

### Core Functions
- **Input Validation**  
  Functions like `validate_carrier_fields`, `validate_skid_count`, and `get_delivery_instructions` enforce consistency across entries based on carrier requirements.
- **Data Formatting**  
  Utilities like `process_order_number`, `clean_text_refined`, and `format_city_province` standardize formatting for cleaner input management.

---

## **PDF Generation Module (`pdf_generator.py`)**

### Overview
The `pdf_generator.py` module generates and fills out **Bill of Lading (BOL)** and **shipping label PDFs**. Data mapping and field filling are performed dynamically, ensuring organized, well-formatted documents.

### Key Features
- **Template-Based Field Population**: Uses a `data_map` to populate fields based on structured order data, with fields like `AddInfo7` and `AddInfo8` used to handle longer delivery instructions.
- **Dynamic BOL and Label Generation**: Creates BOLs and labels, storing each file in a date-based folder structure to simplify organization.
- **Automated Field Adjustments**: Functions like `center_text_x` and `adjust_font_size` manage text alignment and font size to improve readability.

### Core Functions
- **PDF Filling and Label Generation**  
  `fill_pdf` populates templates, and `generate_labels` creates structured shipping labels with tracking information.
- **Data Preparation**  
  `prepare_data_map` assembles user inputs and order data, applying carrier-specific requirements and organizing delivery instructions for readability.
- **BOL and Label Saving**  
  `generate_bol` oversees the full process, generating the BOL, creating labels, and saving each document in organized, date-based folders.

---

## **Utilities Module (`utils.py`)**

### Overview
`utils.py` provides foundational utilities for **logging**, **path handling**, and **text formatting**. These functions support consistent file management, error tracking, and layout across modules.

### Key Features
- **Date-Based Directory Organization**: Organizes output files by creation date (`Month YYYY/Month DD`), aiding in file retrieval and storage.
- **Centralized Logging**: Functions like `log_info` and `log_error` keep records of successful operations and issues.
- **Text Formatting for PDFs**: `center_text_x` and `adjust_font_size` enable dynamic layout adjustments for optimal readability within PDF fields.

### Core Functions
- **File and Directory Handling**  
  `get_full_path` converts paths, and `ensure_directory_exists_with_date` creates date-organized folders for structured file storage.
- **Text Layout Utilities**  
  `center_text_x` and `adjust_font_size` optimize text layout in PDF fields for better presentation.
- **Validation Utilities**  
  Functions like `validate_alphanumeric`, `validate_numeric_field`, and `validate_order_number` standardize input validation.

---
