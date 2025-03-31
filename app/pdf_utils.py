# File: app/pdf_utils.py

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def fill_prescription_form(
    template_path: str,
    output_path: str,
    form_data: Dict[str, str],
    field_mappings: Dict[int, str],
    first_tab_index: int,
    medications: List[Dict[str, Any]],
    medications_per_page: int = 15,
) -> bool:
    """
    Fill a PDF prescription form with the given data.

    Args:
        template_path: Path to the template PDF file
        output_path: Path where the filled PDF will be saved
        form_data: Dictionary with form field data (patient info, etc.)
        field_mappings: Dictionary mapping column numbers to medication attributes
        first_tab_index: Tab index of the first field in the form
        medications: List of medication dictionaries with data to fill
        medications_per_page: Maximum number of medications per page

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if template exists
        if not os.path.exists(template_path):
            logger.error(f"Template file not found: {template_path}")
            return False

        # Open the template PDF
        with open(template_path, "rb") as template_file:
            pdf_reader = PdfReader(template_file)
            pdf_writer = PdfWriter()

            # Get the first page
            template_page = pdf_reader.pages[0]

            # Add the page to the writer
            pdf_writer.add_page(template_page)

            # Get form fields
            form_fields = pdf_reader.get_fields()

            if not form_fields:
                logger.error("No form fields found in the template PDF")
                return False

            # Fill basic form data (patient info, etc.)
            for field_name, value in form_data.items():
                if field_name in form_fields:
                    pdf_writer.update_page_form_field_values(0, {field_name: value})

            # Fill medication data
            num_meds = min(len(medications), medications_per_page)

            for i in range(num_meds):
                med = medications[i]

                # Calculate base tab index for this medication row
                row_base_index = first_tab_index + (i * len(field_mappings))

                # Fill each field according to the mappings
                for col_num, field_attr in field_mappings.items():
                    # Calculate the field index for this cell
                    field_index = row_base_index + int(col_num) - 1
                    field_name = f"field{field_index}"

                    # Get the value from the medication for this field
                    value = med.get(field_attr, "")

                    # Update the field
                    pdf_writer.update_page_form_field_values(
                        0, {field_name: str(value)}
                    )

            # Save the modified PDF
            with open(output_path, "wb") as output_file:
                pdf_writer.write(output_file)

            return True

    except Exception as e:
        logger.error(f"Error filling prescription form: {e}")
        return False


def generate_prescription_pdf(
    order_id: int, template_id: Optional[int] = None
) -> Optional[str]:
    """
    Generate a filled prescription PDF for the given order.

    Args:
        order_id: ID of the order to generate PDF for
        template_id: Optional ID of the template to use (uses active template if None)

    Returns:
        Path to the generated PDF file or None if generation failed
    """
    from models import Order, PrescriptionTemplate

    try:
        # Get the order
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return None

        # Get template
        template = None
        if template_id:
            template = PrescriptionTemplate.query.get(template_id)
        else:
            template = PrescriptionTemplate.get_active_template()

        if not template:
            logger.error("No active prescription template found")
            return None

        # Create data for the form
        form_data = {
            # Add patient-specific fields here
            "datum": order.hospital_visit.visit_date.strftime("%d.%m.%Y"),
            "name": order.hospital_visit.notes
            or "",  # You might want to add patient name fields
        }

        # Create medication data
        medications = []
        for item in order.order_items:
            med = item.medication

            # Create a dictionary with all possible fields
            med_data = {
                "medication_name": med.name,
                "active_ingredient": med.active_ingredient or "",
                "form": med.form or "",
                "dosage": med.dosage,
                "frequency": med.frequency,
                "daily_usage": med.daily_usage,
                "package_size_n1": med.package_size_n1,
                "package_size_n2": med.package_size_n2,
                "package_size_n3": med.package_size_n3,
                "quantity_needed": item.quantity_needed,
                "packages_n1": item.packages_n1,
                "packages_n2": item.packages_n2,
                "packages_n3": item.packages_n3,
                "notes": med.notes or "",
            }

            medications.append(med_data)

        # Create the output directory if it doesn't exist
        from flask import current_app

        output_dir = os.path.join(current_app.root_path, "data", "prescriptions")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"prescription_order_{order_id}_{timestamp}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        # Fill the form
        success = fill_prescription_form(
            template_path=template.template_path,
            output_path=output_path,
            form_data=form_data,
            field_mappings=template.column_mapping_dict,
            first_tab_index=template.first_field_tab_index,
            medications=medications,
            medications_per_page=template.medications_per_page,
        )

        if success:
            return output_path
        else:
            return None

    except Exception as e:
        logger.error(f"Error generating prescription PDF: {e}")
        return None
