"""PDF Utilities for generating order PDFs.

This module provides functionality to fill a PDF order form
"""

# Standard library imports
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
from pypdf import PdfReader, PdfWriter

# Create a logger for this module
logger = logging.getLogger(__name__)



def generate_order_pdf(
    order_id: int, template_id: Optional[int] = None
) -> Optional[str]:
    """
    Generate a filled order PDF for the given order.

    Args:
        order_id: ID of the order to generate PDF for
        template_id: Optional ID of the template to use (uses physician's template if None)

    Returns:
        Path to the generated PDF file or None if generation failed
    """
    from models import Order, PDFTemplate

    try:
        # Get the order
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return None

        # Get template from physician or use specified template
        pdf_template = None
        
        if template_id:
            pdf_template = PDFTemplate.query.get(template_id)
        else:
            # Check if physician has a PDF template assigned
            if order.physician_visit and order.physician_visit.physician and order.physician_visit.physician.pdf_template:
                pdf_template = order.physician_visit.physician.pdf_template

        if not pdf_template:
            logger.error("No PDF template assigned to physician")
            return None

        # Create data for the form
        form_data = {
            # Add patient-specific fields here
            "datum": order.physician_visit.visit_date.strftime("%d.%m.%Y"),
            "name": order.physician_visit.notes
            or "",  # You might want to add patient name fields
        }

        # Use the PDFTemplate system
        if not pdf_template.column_formulas:
            logger.error(f"PDFTemplate {pdf_template.id} is not fully configured")
            return None
            
        # Generate PDF using PDFTemplate's function
        from routes.pdf_mapper import generate_filled_pdf_from_template
        
        # Get medications from order items
        order_medications = [item.medication for item in order.order_items]
        
        # Create the output directory if it doesn't exist
        from utils import get_data_directory
        output_dir = os.path.join(get_data_directory(), "orders")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"order_{order_id}_{timestamp}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            # Generate the PDF and save to our desired location
            temp_path = generate_filled_pdf_from_template(pdf_template, order_medications)
            
            # Move the temp file to our desired location
            import shutil
            shutil.move(temp_path, output_path)
            
            return output_path
        except FileNotFoundError as e:
            logger.error(f"PDF template file not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating PDF with PDFTemplate: {e}")
            return None

    except Exception as e:
        logger.error(f"Error generating order PDF: {e}")
        return None
