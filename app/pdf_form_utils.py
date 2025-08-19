"""
PDF Form utilities for detecting tables, creating fields, and filling forms.
"""

import logging
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject, 
    TextStringObject, 
    ArrayObject,
    DictionaryObject,
    NumberObject,
    BooleanObject
)
import tempfile

logger = logging.getLogger(__name__)


def detect_table_in_pdf(pdf_path, page_number=0):
    """
    Detect table structure in a PDF page.
    
    This is a simplified implementation. In production, you would use
    computer vision libraries like OpenCV or table detection libraries.
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            if page_number >= len(pdf_reader.pages):
                return None
            
            page = pdf_reader.pages[page_number]
            
            # Get page dimensions
            mediabox = page.mediabox
            page_width = float(mediabox.width)
            page_height = float(mediabox.height)
            
            # Estimate table area (assuming it takes most of the page)
            # In a real implementation, you'd use OCR or pattern detection
            table_info = {
                'page_width': page_width,
                'page_height': page_height,
                'table_top': page_height * 0.8,  # Top 80% of page
                'table_bottom': page_height * 0.1,  # Bottom 10% of page
                'table_left': page_width * 0.05,  # 5% margin
                'table_right': page_width * 0.95,  # 5% margin
                'estimated': True
            }
            
            return table_info
            
    except Exception as e:
        logger.error(f"Error detecting table: {e}")
        return None


def create_form_fields(pdf_path, output_path, rows, columns, table_info=None):
    """
    Add form fields to a PDF for table cells.
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            pdf_writer = PdfWriter()
            
            # Copy all pages
            for page_num, page in enumerate(pdf_reader.pages):
                pdf_writer.add_page(page)
                
                # Add fields only to first page (or as configured)
                if page_num == 0:
                    # Get page dimensions
                    mediabox = page.mediabox
                    page_width = float(mediabox.width)
                    page_height = float(mediabox.height)
                    
                    # Use provided table info or estimate
                    if not table_info:
                        table_info = {
                            'table_top': page_height * 0.8,
                            'table_bottom': page_height * 0.1,
                            'table_left': page_width * 0.05,
                            'table_right': page_width * 0.95
                        }
                    
                    # Calculate cell dimensions
                    table_width = table_info['table_right'] - table_info['table_left']
                    table_height = table_info['table_top'] - table_info['table_bottom']
                    cell_width = table_width / columns
                    cell_height = table_height / rows
                    
                    # Create fields for each cell
                    for row in range(rows):
                        for col in range(columns):
                            field_name = f"row_{row + 1}_col_{col + 1}"
                            
                            # Calculate field position
                            x = table_info['table_left'] + (col * cell_width)
                            y = table_info['table_top'] - ((row + 1) * cell_height)
                            
                            # Create text field annotation
                            field = create_text_field(
                                field_name,
                                x, y,
                                cell_width * 0.9,  # Leave some margin
                                cell_height * 0.8,
                                page_num
                            )
                            
                            # Add field to writer
                            pdf_writer.add_annotation(page_num, field)
            
            # Write output
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            return True
            
    except Exception as e:
        logger.error(f"Error creating form fields: {e}")
        return False


def create_text_field(name, x, y, width, height, page_num):
    """
    Create a text field annotation for PDF.
    """
    field = DictionaryObject()
    
    field.update({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/FT"): NameObject("/Tx"),  # Text field
        NameObject("/T"): TextStringObject(name),  # Field name
        NameObject("/V"): TextStringObject(""),  # Field value (empty initially)
        NameObject("/Rect"): ArrayObject([
            NumberObject(x),
            NumberObject(y),
            NumberObject(x + width),
            NumberObject(y + height)
        ]),
        NameObject("/F"): NumberObject(4),  # Field flags
        NameObject("/P"): NumberObject(page_num),  # Page reference
        NameObject("/DA"): TextStringObject("/Helv 10 Tf 0 g"),  # Default appearance
        NameObject("/Ff"): NumberObject(0),  # Field flags (0 = no special flags)
    })
    
    # Add appearance stream for better compatibility
    field[NameObject("/AP")] = DictionaryObject()
    field[NameObject("/AP")][NameObject("/N")] = DictionaryObject()
    
    return field


def apply_field_mappings(pdf_path, output_path, field_mappings, data_rows):
    """
    Fill PDF form fields with data according to mappings.
    
    Args:
        pdf_path: Path to PDF with form fields
        output_path: Where to save filled PDF
        field_mappings: Dictionary of field names to data keys
        data_rows: List of dictionaries with data to fill
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            pdf_writer = PdfWriter()
            
            # Clone the reader to writer
            pdf_writer.clone_reader_document_root(pdf_reader)
            
            # Get form fields
            if "/AcroForm" in pdf_reader.trailer["/Root"]:
                form = pdf_reader.trailer["/Root"]["/AcroForm"]
                fields = form.get("/Fields", [])
                
                # Process each data row
                for row_idx, data_row in enumerate(data_rows):
                    if row_idx >= len(fields):
                        break  # No more fields available
                    
                    # Fill fields for this row
                    for field_ref in fields:
                        field = field_ref.get_object()
                        field_name = field.get("/T", "")
                        
                        # Check if this field matches our row pattern
                        if field_name.startswith(f"row_{row_idx + 1}_"):
                            # Extract column number
                            col_match = field_name.split("_col_")
                            if len(col_match) == 2:
                                col_num = col_match[1]
                                
                                # Get mapping for this column
                                if col_num in field_mappings:
                                    mapping = field_mappings[col_num]
                                    
                                    # Build field value from mapping
                                    if isinstance(mapping, dict):
                                        # Formula with multiple fields
                                        values = []
                                        for data_key in mapping.get('fields', []):
                                            if data_key in data_row:
                                                values.append(str(data_row[data_key]))
                                        
                                        field_value = mapping.get('separator', ' ').join(values)
                                    else:
                                        # Simple field mapping
                                        field_value = str(data_row.get(mapping, ''))
                                    
                                    # Update field value
                                    pdf_writer.update_page_form_field_values(
                                        pdf_reader.pages[0],
                                        {field_name: field_value}
                                    )
            
            # Write output
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            return True
            
    except Exception as e:
        logger.error(f"Error applying field mappings: {e}")
        return False


def generate_filled_pdf(template, medications, output_path=None):
    """
    Generate a filled PDF from template with medication data.
    
    Args:
        template: PDFTemplate object
        medications: List of medication objects
        output_path: Optional output path, generates temp file if not provided
    
    Returns:
        Path to generated PDF
    """
    if not output_path:
        output_path = Path(tempfile.gettempdir()) / f"filled_{template.id}.pdf"
    
    # Prepare data rows
    data_rows = []
    for med in medications:
        # Extract medication data
        product = med.default_product or (med.migrated_product[0] if med.migrated_product else None)
        
        row_data = {
            'brand_name': product.brand_name if product else med.name,
            'manufacturer': product.manufacturer if product else '',
            'display_name': product.display_name if product else med.name,
            'active_ingredient': product.active_ingredient.name if product and product.active_ingredient else med.active_ingredient,
            'strength': product.active_ingredient.strength if product and product.active_ingredient else med.dosage,
            'unit': product.active_ingredient.unit if product and product.active_ingredient else med.unit,
            'package_size': 'N1',  # Default, would come from actual package
            'quantity': med.package_size_n1 or 0,
            'physician': med.physician.display_name if med.physician else '',
            'dosage': f"{med.dosage} {med.unit}" if med.dosage else '',
            'instructions': med.notes or ''
        }
        data_rows.append(row_data)
    
    # Apply field mappings
    from flask import current_app
    pdf_path = Path(current_app.root_path) / template.file_path
    
    success = apply_field_mappings(
        pdf_path,
        output_path,
        template.column_formulas or {},
        data_rows
    )
    
    if success:
        return str(output_path)
    else:
        return None


def set_tab_order(pdf_path, output_path, field_order):
    """
    Set the tab order for form fields in a PDF.
    
    Args:
        pdf_path: Input PDF path
        output_path: Output PDF path
        field_order: List of field names in desired tab order
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            pdf_writer = PdfWriter()
            
            # Clone the reader
            pdf_writer.clone_reader_document_root(pdf_reader)
            
            # Get form fields
            if "/AcroForm" in pdf_reader.trailer["/Root"]:
                form = pdf_reader.trailer["/Root"]["/AcroForm"]
                fields = form.get("/Fields", [])
                
                # Create a mapping of field names to field objects
                field_map = {}
                for field_ref in fields:
                    field = field_ref.get_object()
                    field_name = field.get("/T", "")
                    if field_name:
                        field_map[str(field_name)] = field_ref
                
                # Reorder fields according to specified order
                ordered_fields = []
                for field_name in field_order:
                    if field_name in field_map:
                        ordered_fields.append(field_map[field_name])
                
                # Add any remaining fields not in the order
                for field_name, field_ref in field_map.items():
                    if field_name not in field_order:
                        ordered_fields.append(field_ref)
                
                # Update the form fields array
                form[NameObject("/Fields")] = ArrayObject(ordered_fields)
            
            # Write output
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            return True
            
    except Exception as e:
        logger.error(f"Error setting tab order: {e}")
        return False