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

        # Use the PDFTemplate system
        if not pdf_template.column_formulas:
            logger.error(f"PDFTemplate {pdf_template.id} is not fully configured")
            return None
            
        # Generate PDF using clean order-based approach
        return generate_filled_pdf_from_order(pdf_template, order)

    except Exception as e:
        logger.error(f"Error generating order PDF: {e}")
        return None


def generate_filled_pdf_from_order(template, order) -> Optional[str]:
    """
    Generate a filled PDF from template using order data.
    
    Args:
        template: PDFTemplate instance
        order: Order instance
        
    Returns:
        Path to generated PDF file or None if failed
    """
    import tempfile
    from pathlib import Path
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    
    try:
        # Resolve PDF path
        from routes.pdf_mapper import resolve_pdf_path
        pdf_path = resolve_pdf_path(template)
        
        # Create output path
        output_path = (
            Path(tempfile.gettempdir())
            / f"order_{order.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
        logger.info(f"Generating order PDF for order {order.id} using template {template.id}")
        
        with open(pdf_path, "rb") as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            pdf_writer = PdfWriter()
            
            # Prepare field data from order
            field_updates = {}
            
            for row_idx, item in enumerate(order.order_items, 1):
                # Get ingredient and product - handle both new and transitional cases
                ingredient = None
                product = None
                
                if item.product and item.product.active_ingredient:
                    # New system: item -> product -> ingredient
                    product = item.product
                    ingredient = product.active_ingredient
                elif item.active_ingredient:
                    # Transitional: item -> ingredient directly
                    ingredient = item.active_ingredient
                    # Try to find a default product for this ingredient
                    product = ingredient.default_product or (ingredient.products[0] if ingredient.products else None)
                else:
                    logger.warning(f"Order item {item.id} has no ingredient or product")
                    continue
                
                # Determine package size and quantity
                package_size = "N1"
                packages_count = item.packages_n1 or 0
                
                if item.packages_n2 and item.packages_n2 > 0:
                    package_size = "N2" 
                    packages_count = item.packages_n2
                elif item.packages_n3 and item.packages_n3 > 0:
                    package_size = "N3"
                    packages_count = item.packages_n3
                
                # Calculate daily units from schedules (placeholder for now)
                daily_units_count = ingredient.daily_usage if hasattr(ingredient, 'daily_usage') else 0
                
                # Extract component strengths and units
                component_strengths = []
                component_units = []
                
                if ingredient.components:
                    for comp in ingredient.components:
                        # Format strength to remove unnecessary decimal places
                        strength_float = float(comp.strength)
                        if strength_float == int(strength_float):
                            strength_str = str(int(strength_float))
                        else:
                            strength_str = f"{strength_float:g}"
                        component_strengths.append(strength_str)
                        component_units.append(comp.strength_unit)
                
                component_strengths_formatted = "/".join(component_strengths) if component_strengths else ""
                
                # For units, check if all are the same - if so, use just one
                if component_units:
                    unique_units = list(set(component_units))
                    if len(unique_units) == 1:
                        # All units are the same, use just one
                        component_units_formatted = unique_units[0]
                    else:
                        # Different units, use the format with slashes
                        component_units_formatted = "/".join(component_units)
                else:
                    component_units_formatted = ""
                
                # Build data for this row
                row_data = {
                    "display_name": product.display_name if product else ingredient.component_display,
                    "brand_name": product.brand_name if product else ingredient.component_display,
                    "manufacturer": product.manufacturer if product else "",
                    "ingredient_name": ingredient.name,  # General name (e.g., "Kaftrio")
                    "component_display": ingredient.component_display,  # Full components (e.g., "Ivacaftor 75mg + Tezacaftor 50mg + Elexacaftor 100mg")
                    "component_strengths": component_strengths_formatted,  # Strengths only (e.g., "75/50/100")
                    "component_units": component_units_formatted,  # Units only (e.g., "mg/mg/mg")
                    "dosage_form": ingredient.form or "tablets",
                    "package_size_ordered": package_size,
                    "packages_ordered": str(packages_count),
                    "daily_units": str(int(daily_units_count)) if daily_units_count > 0 else "",
                    "daily_units_formatted": f"{int(daily_units_count)} units" if daily_units_count > 0 else ""
                }
                
                logger.debug(f"Row {row_idx}: {ingredient.component_display} - {packages_count} x {package_size}")
                
                # Apply column formulas to generate field values
                for col_idx in range(1, template.columns_count + 1):
                    mapping_key = f"{row_idx}_{col_idx}"
                    
                    if (template.structure_mapping and 
                        mapping_key in template.structure_mapping):
                        
                        field_name = template.structure_mapping[mapping_key].get("field", "")
                        if not field_name:
                            continue
                            
                        # Get column formula
                        formula = template.column_formulas.get(str(col_idx), {})
                        if not formula:
                            continue
                            
                        # Build field value from formula
                        field_values = []
                        for field_key in formula.get("fields", []):
                            value = row_data.get(field_key, "")
                            if value:
                                field_values.append(str(value))
                        
                        field_value = formula.get("separator", " ").join(field_values)
                        field_updates[field_name] = field_value
                        
                        logger.debug(f"Field {field_name} = {field_value}")
            
            # Apply field updates to PDF
            if field_updates:
                logger.info(f"Updating {len(field_updates)} PDF fields")
                
                # Copy pages
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                # Copy form structure
                if "/AcroForm" in pdf_reader.trailer["/Root"]:
                    pdf_writer._root_object.update({
                        NameObject("/AcroForm"): pdf_reader.trailer["/Root"]["/AcroForm"]
                    })
                
                # Update fields
                for field_name, field_value in field_updates.items():
                    try:
                        pdf_writer.update_page_form_field_values(
                            pdf_writer.pages[0],
                            {field_name: field_value}
                        )
                    except Exception as e:
                        logger.warning(f"Could not update field {field_name}: {e}")
            else:
                # No fields to update, just copy pages
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            
            # Write output
            with open(output_path, "wb") as output_file:
                pdf_writer.write(output_file)
            
            logger.info(f"Generated PDF saved to: {output_path}")
            return str(output_path)
            
    except Exception as e:
        logger.error(f"Error generating order PDF: {e}")
        return None
