"""
PDF Form Mapper routes for creating and managing PDF templates with field mappings.
"""

import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    send_file,
    current_app,
)
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject,
    TextStringObject,
    ArrayObject,
    DictionaryObject,
    BooleanObject,
)

from models import (
    db,
    PDFTemplate,
    Medication,
    MedicationProduct,
    ActiveIngredient,
)
from pdf_form_utils import (
    detect_table_in_pdf,
    create_form_fields,
    apply_field_mappings,
    generate_filled_pdf,
)

bp = Blueprint("pdf_mapper", __name__, url_prefix="/pdf-mapper")

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf"}


def validate_and_clean_strength(value):
    """Validate and clean strength value to ensure it's numeric.
    
    Args:
        value: The strength value to validate (can be string, number, etc.)
    
    Returns:
        str: Cleaned numeric string with dot as decimal separator, or empty string if invalid
    """
    if not value:
        return ""
    
    # Convert to string and strip whitespace
    str_value = str(value).strip()
    
    if not str_value:
        return ""
    
    # Replace comma with dot for decimal separator
    str_value = str_value.replace(',', '.')
    
    # Remove any non-numeric characters except dot and minus
    import re
    # Match optional minus, digits, optional decimal point and more digits
    match = re.match(r'^-?\d+(\.\d+)?$', str_value)
    
    if match:
        # Valid number format
        return str_value
    else:
        # Try to extract just the numeric part (e.g., "400mg" -> "400")
        match = re.match(r'^(-?\d+(?:\.\d+)?)', str_value)
        if match:
            return match.group(1)
        else:
            # No valid number found
            return ""


def allowed_file(filename):
    """Check if file has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def resolve_pdf_path(template):
    """Resolve the actual file path for a PDF template, handling Docker and local environments."""
    import logging

    logger = logging.getLogger(__name__)

    # Extract just the filename from the stored path
    filename = Path(template.file_path).name

    # Get data directory (where database is stored)
    # Use /app/data as the persistent storage location
    data_dir = Path("/app/data")

    # Try various locations where the file might be
    paths_to_try = [
        # Try the stored path as-is (if it's absolute)
        (
            Path(template.file_path)
            if os.path.isabs(template.file_path)
            else None
        ),
        # Primary location: persistent data directory
        data_dir / "pdf_templates" / filename,
        # Fallback: just the filename in pdf_templates
        Path("/app/data/pdf_templates") / filename,
        # Legacy paths for backward compatibility
        Path("/pdf_templates") / filename,
        Path(current_app.root_path) / "static" / "pdf_templates" / filename,
    ]

    for path in paths_to_try:
        if path and path.exists():
            logger.debug(f"Found PDF file at: {path}")
            return path

    # Log all paths tried for debugging
    tried_paths = [str(p) for p in paths_to_try if p]
    logger.error(f"PDF file not found. Tried paths: {tried_paths}")

    # If nothing found, raise error with helpful message
    raise FileNotFoundError(
        f"PDF file '{filename}' not found. Please re-upload the PDF template. Tried paths: {', '.join(tried_paths[:3])}"
    )


@bp.route("/")
def index():
    """List all PDF templates."""
    templates = (
        PDFTemplate.query.filter_by(is_active=True)
        .order_by(PDFTemplate.created_at.desc())
        .all()
    )

    # Check if template files exist
    for template in templates:
        try:
            pdf_path = resolve_pdf_path(template)
            template.file_exists = True
        except FileNotFoundError:
            template.file_exists = False

    return render_template("pdf_mapper/index.html", templates=templates)


@bp.route("/new", methods=["GET", "POST"])
def new_template():
    """Create a new PDF template."""
    if request.method == "POST":
        # Check if file was uploaded
        if "pdf_file" not in request.files:
            flash(_("No PDF file uploaded"), "error")
            return redirect(request.url)

        file = request.files["pdf_file"]
        if file.filename == "":
            flash(_("No file selected"), "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Save the uploaded file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"

            # Create upload directory in persistent data directory (same as database)
            # This ensures PDFs persist across container restarts
            data_dir = Path("/app/data")
            upload_dir = data_dir / "pdf_templates"
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / unique_filename
            file.save(str(file_path))

            # Log the saved path for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Saved PDF file to: {file_path}")

            # Store the absolute path since we're using a data directory outside app root
            # This ensures we can always find the file regardless of the working directory
            stored_path = str(file_path)

            # Create template record
            template = PDFTemplate(
                name=request.form.get("name", filename),
                description=request.form.get("description"),
                filename=filename,
                file_path=stored_path,
                rows_per_page=int(request.form.get("rows_per_page", 20)),
                columns_count=int(request.form.get("columns_count", 5)),
                mapping_step="structure",  # Start with structure mapping
            )

            db.session.add(template)
            db.session.commit()

            flash(
                _(
                    "PDF template uploaded successfully. Please map the PDF form fields to the table structure."
                ),
                "success",
            )
            return redirect(
                url_for("pdf_mapper.structure_view", id=template.id)
            )
        else:
            flash(_("Invalid file type. Only PDF files are allowed"), "error")

    return render_template("pdf_mapper/new.html")


@bp.route("/template/<int:id>/edit")
def edit_template(id):
    """Redirect to appropriate editing view based on mapping step."""
    template = PDFTemplate.query.get_or_404(id)

    # Redirect based on current mapping step
    if template.mapping_step == "structure" or not template.structure_mapping:
        return redirect(url_for("pdf_mapper.structure_view", id=id))
    else:
        return redirect(url_for("pdf_mapper.content_view", id=id))


@bp.route("/template/<int:id>/structure")
def structure_view(id):
    """Edit PDF structure - map form fields to table grid."""
    template = PDFTemplate.query.get_or_404(id)

    # Get detected fields from table_config if available
    detected_fields = []
    if template.table_config and "fields" in template.table_config:
        detected_fields = sorted(
            template.table_config["fields"],
            key=lambda x: x.get("name", "").lower(),
        )

    # Generate simple column headers based on template's column count
    column_headers = []
    for i in range(1, template.columns_count + 1):
        column_headers.append(
            {"id": f"col_{i}", "label": f'{_("Column")} {i}'}
        )

    return render_template(
        "pdf_mapper/structure.html",
        template=template,
        detected_fields=detected_fields,
        column_headers=column_headers,
    )


@bp.route("/template/<int:id>/content")
def content_view(id):
    """Edit PDF content - map data fields to columns."""
    template = PDFTemplate.query.get_or_404(id)

    # Get available data fields from models
    available_fields = {
        "product": [
            {"id": "brand_name", "label": _("Brand Name"), "icon": "📦"},
            {"id": "manufacturer", "label": _("Manufacturer"), "icon": "🏭"},
            {
                "id": "display_name",
                "label": _("Full Product Name"),
                "icon": "📝",
            },
        ],
        "ingredient": [
            {
                "id": "active_ingredient",
                "label": _("Active Ingredient"),
                "icon": "💊",
            },
            {"id": "strength", "label": _("Strength"), "icon": "💪"},
            {"id": "unit", "label": _("Unit"), "icon": "📏"},
        ],
        "dosage": [
            {"id": "daily_units", "label": _("Daily Units"), "icon": "🔢"},
            {
                "id": "dosage_form",
                "label": _("Dosage Form (tablets, etc.)"),
                "icon": "💊",
            },
            {
                "id": "strength_value",
                "label": _("Strength Value"),
                "icon": "💪",
            },
            {
                "id": "strength_unit",
                "label": _("Strength Unit (mg, ml, etc.)"),
                "icon": "📏",
            },
            {
                "id": "daily_dosage",
                "label": _("Daily Dosage (Strength × Units)"),
                "icon": "➕",
            },
        ],
        "package": [
            {"id": "package_size", "label": _("Package Size"), "icon": "📦"},
            {
                "id": "quantity",
                "label": _("Quantity per Package"),
                "icon": "🔢",
            },
            {"id": "pzn", "label": _("PZN"), "icon": "🔖"},
            {"id": "gtin", "label": _("GTIN"), "icon": "📊"},
        ],
        "order": [
            {
                "id": "packages_ordered",
                "label": _("Number of Packages"),
                "icon": "📦",
            },
            {
                "id": "package_size_ordered",
                "label": _("Package Size (N1/N2/N3)"),
                "icon": "📏",
            },
            {"id": "total_units", "label": _("Total Units"), "icon": "🔢"},
            {"id": "days_supply", "label": _("Days Supply"), "icon": "📅"},
            {"id": "months_supply", "label": _("Months Supply"), "icon": "📅"},
        ],
        "order_info": [
            {"id": "physician", "label": _("Physician"), "icon": "👨‍⚕️"},
            {"id": "instructions", "label": _("Instructions"), "icon": "📋"},
            {"id": "notes", "label": _("Notes"), "icon": "📝"},
        ],
    }

    return render_template(
        "pdf_mapper/content.html",
        template=template,
        available_fields=available_fields,
    )


@bp.route("/template/<int:id>/detect-fields", methods=["POST"])
def detect_fields(id):
    """Detect existing form fields in PDF or create new ones if needed."""
    template = PDFTemplate.query.get_or_404(id)

    try:
        # Read the PDF using the helper function
        pdf_path = resolve_pdf_path(template)

        # First, check if the PDF already has form fields
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        existing_fields = []

        if reader.get_form_text_fields():
            # PDF already has form fields - just detect and use them
            for page_num, page in enumerate(reader.pages):
                if "/Annots" in page:
                    for annot_ref in page["/Annots"]:
                        annot = annot_ref.get_object()
                        if annot.get("/T"):  # Field name
                            field_name = annot["/T"]
                            field_type = annot.get(
                                "/FT", "/Tx"
                            )  # Default to text
                            existing_fields.append(
                                {
                                    "name": str(field_name),
                                    "page": page_num,
                                    "type": "text",
                                }
                            )

            # Sort fields by name
            existing_fields_sorted = sorted(
                existing_fields, key=lambda x: x.get("name", "").lower()
            )

            # Store the existing fields configuration
            template.table_config = {
                "fields": existing_fields_sorted,
                "detected_at": datetime.utcnow().isoformat(),
                "has_form_fields": True,
                "existing_fields": True,
                "fields_count": len(existing_fields_sorted),
            }

            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": _(
                        "Found %(count)s existing form fields in PDF",
                        count=len(existing_fields_sorted),
                    ),
                    "fields": existing_fields_sorted,
                    "existing_fields": True,
                    "fields_count": len(existing_fields_sorted),
                }
            )

        # No existing fields found - offer to create grid-based fields
        return jsonify(
            {
                "success": False,
                "message": _(
                    "No form fields found in PDF. Would you like to create a grid of fields?"
                ),
                "existing_fields": False,
                "needs_creation": True,
            }
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error detecting fields: {str(e)}")

        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template/<int:id>/create-grid-fields", methods=["POST"])
def create_grid_fields(id):
    """Create a grid of form fields in PDF (only if no fields exist)."""
    template = PDFTemplate.query.get_or_404(id)

    try:
        # Read the PDF using the helper function
        pdf_path = resolve_pdf_path(template)

        # Create a temporary file for the PDF with form fields
        temp_pdf_path = (
            pdf_path.parent
            / f"temp_{template.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        # Detect table structure
        table_info = detect_table_in_pdf(str(pdf_path))

        # Create form fields in the PDF
        success = create_form_fields(
            str(pdf_path),
            str(temp_pdf_path),
            template.rows_per_page,
            template.columns_count,
            table_info,
        )

        if success:
            # Replace the original PDF with the one containing form fields
            import shutil

            shutil.move(str(temp_pdf_path), str(pdf_path))

            # Generate field configuration
            fields = []
            for row in range(1, template.rows_per_page + 1):
                for col in range(1, template.columns_count + 1):
                    field_name = f"row_{row}_col_{col}"
                    fields.append(
                        {
                            "name": field_name,
                            "row": row,
                            "column": col,
                            "type": "text",
                        }
                    )

            # Sort fields by name for consistent display
            fields = sorted(fields, key=lambda x: x.get("name", "").lower())

            # Store table configuration
            template.table_config = {
                "rows": template.rows_per_page,
                "columns": template.columns_count,
                "fields": fields,
                "detected_at": datetime.utcnow().isoformat(),
                "has_form_fields": True,
                "grid_created": True,
            }

            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": _(
                        "Created %(count)s form fields in a %(rows)sx%(cols)s grid",
                        count=len(fields),
                        rows=template.rows_per_page,
                        cols=template.columns_count,
                    ),
                    "fields_count": len(fields),
                }
            )
        else:
            # Clean up temp file if it exists
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()

            return (
                jsonify(
                    {
                        "success": False,
                        "error": _("Failed to create form fields in PDF"),
                    }
                ),
                500,
            )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error creating grid fields: {str(e)}")

        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template/<int:id>/save-structure", methods=["POST"])
def save_structure(id):
    """Save PDF field structure mapping."""
    template = PDFTemplate.query.get_or_404(id)

    data = request.json

    # Save structure mapping (grid positions)
    if "structure_mapping" in data:
        template.structure_mapping = data["structure_mapping"]
        # Mark that structure is complete, move to content step
        template.mapping_step = "content"

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": _("Structure mapping saved successfully"),
            "redirect": url_for("pdf_mapper.content_view", id=id),
        }
    )


@bp.route("/template/<int:id>/save-mappings", methods=["POST"])
def save_mappings(id):
    """Save field mappings and column formulas."""
    template = PDFTemplate.query.get_or_404(id)

    data = request.json

    # Save field mappings
    if "field_mappings" in data:
        template.field_mappings = data["field_mappings"]

    # Save column formulas
    if "column_formulas" in data:
        template.column_formulas = data["column_formulas"]

    # Save tab order
    if "tab_order" in data:
        template.tab_order = data["tab_order"]

    db.session.commit()

    return jsonify(
        {"success": True, "message": _("Mappings saved successfully")}
    )


@bp.route("/template/<int:id>/preview", methods=["POST"])
def preview_template(id):
    """Preview PDF with sample data."""
    template = PDFTemplate.query.get_or_404(id)

    # Get sample medications
    sample_medications = []
    medications = Medication.query.limit(5).all()

    for med in medications:
        # Get product and ingredient information
        product = med.default_product or (
            med.migrated_product[0] if med.migrated_product else None
        )

        # Calculate daily units from schedules or use daily_usage
        daily_units = med.daily_usage if med.daily_usage > 0 else 0

        # Get strength value and unit
        strength_value = ""
        strength_unit = ""
        if product and product.active_ingredient:
            raw_strength = (
                product.active_ingredient.strength
                if product.active_ingredient.strength
                else med.dosage if med.dosage else ""
            )
            # Validate and clean the strength value
            strength_value = validate_and_clean_strength(raw_strength)
            strength_unit = (
                product.active_ingredient.strength_unit
                if product.active_ingredient.strength_unit
                else ""
            )
        else:
            # Parse from medication dosage if available (e.g., "400" from "400mg")
            if med.dosage:
                # Validate and clean the dosage value
                strength_value = validate_and_clean_strength(med.dosage)
            # Try to extract unit from medication name or form field if available
            strength_unit = (
                med.form if hasattr(med, "form") and med.form else "mg"
            )

        # Calculate daily dosage (strength × daily units)
        daily_dosage = ""
        if strength_value and daily_units:
            try:
                # Handle German decimal format (1,25 -> 1.25)
                strength_clean = str(strength_value).replace(',', '.')
                strength_num = float(strength_clean)
                total_dosage = strength_num * daily_units
                # Output only the numeric value without unit
                daily_dosage = f"{total_dosage:.2f}".rstrip('0').rstrip('.')
            except (ValueError, TypeError):
                # Fallback: just return the calculation string without unit
                daily_dosage = f"{daily_units} × {strength_value}"

        # Determine dosage form
        # First try to use the form from the active ingredient
        dosage_form = ""
        if product and product.active_ingredient and product.active_ingredient.form:
            dosage_form = product.active_ingredient.form
        elif hasattr(med, 'form') and med.form:
            dosage_form = med.form
        else:
            # Fallback: try to infer from unit or name
            if strength_unit:
                if "ml" in strength_unit.lower():
                    dosage_form = "ml"
                elif "mg" in strength_unit.lower():
                    dosage_form = "tablets"
            if not dosage_form:  # Still no form determined
                if "drops" in med.name.lower():
                    dosage_form = "drops"
                elif "spray" in med.name.lower():
                    dosage_form = "sprays"
                else:
                    dosage_form = "tablets"  # Final default

        # Calculate order quantities (sample data)
        packages_ordered = 2  # Sample: ordering 2 packages
        package_size_ordered = "N2"  # Sample: N2 package
        quantity_per_package = (
            med.package_size_n2
            if package_size_ordered == "N2"
            else (
                med.package_size_n3
                if package_size_ordered == "N3"
                else med.package_size_n1
            )
        )
        total_units = packages_ordered * (
            quantity_per_package or 50
        )  # Default to 50 if not set
        days_supply = int(total_units / daily_units) if daily_units > 0 else 0
        months_supply = round(days_supply / 30, 1) if days_supply > 0 else 0

        med_data = {
            "brand_name": product.brand_name if product else med.name,
            "manufacturer": product.manufacturer if product else "",
            "display_name": product.display_name if product else med.name,
            "active_ingredient": (
                product.active_ingredient.name
                if product and product.active_ingredient
                else med.active_ingredient
            ),
            "strength": validate_and_clean_strength(
                product.active_ingredient.strength
                if product and product.active_ingredient
                else med.dosage
            ),
            "unit": (
                product.active_ingredient.strength_unit
                if product and product.active_ingredient
                else ""
            ),
            "package_size": "N1",  # Default
            "quantity": med.package_size_n1 or 0,
            "pzn": "",  # Would come from package
            "gtin": "",  # Would come from package
            "physician": med.physician.display_name if med.physician else "",
            "instructions": med.notes or "",
            "notes": med.notes or "",
            # Dosage fields
            "daily_units": str(int(daily_units)) if daily_units > 0 else "",
            "dosage_form": dosage_form,
            "strength_value": strength_value,
            "strength_unit": strength_unit,
            "daily_dosage": daily_dosage,
            # Order fields
            "packages_ordered": str(packages_ordered),
            "package_size_ordered": package_size_ordered,
            "total_units": str(total_units),
            "days_supply": str(days_supply),
            "months_supply": str(months_supply),
        }
        sample_medications.append(med_data)

    try:
        # Generate preview PDF
        preview_path = generate_preview_pdf(template, sample_medications)

        return jsonify(
            {
                "success": True,
                "preview_url": url_for(
                    "pdf_mapper.download_preview", id=template.id
                ),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template/<int:id>/generate", methods=["POST"])
def generate_pdf(id):
    """Generate PDF with actual medication data."""
    template = PDFTemplate.query.get_or_404(id)

    # Get selected medications from request
    medication_ids = request.json.get("medication_ids", [])

    if not medication_ids:
        return jsonify({"error": _("No medications selected")}), 400

    medications = Medication.query.filter(
        Medication.id.in_(medication_ids)
    ).all()

    try:
        # Generate the PDF
        output_path = generate_filled_pdf_from_template(template, medications)

        # Store the path in session for download
        from flask import session

        session["generated_pdf"] = output_path

        return jsonify(
            {
                "success": True,
                "download_url": url_for(
                    "pdf_mapper.download_generated", id=template.id
                ),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template/<int:id>/download-preview")
def download_preview(id):
    """Download preview PDF."""
    template = PDFTemplate.query.get_or_404(id)

    # Get preview path from temp directory
    preview_path = Path(tempfile.gettempdir()) / f"preview_{template.id}.pdf"

    if preview_path.exists():
        return send_file(
            str(preview_path),
            download_name=f"preview_{template.name}.pdf",
            as_attachment=True,
            mimetype="application/pdf",
        )
    else:
        flash(_("Preview not found. Please generate it again."), "error")
        return redirect(url_for("pdf_mapper.edit_template", id=id))


@bp.route("/template/<int:id>/download-generated")
def download_generated(id):
    """Download generated PDF."""
    from flask import session

    template = PDFTemplate.query.get_or_404(id)

    # Get generated path from session
    generated_path = session.get("generated_pdf")

    if generated_path and Path(generated_path).exists():
        return send_file(
            generated_path,
            download_name=f"{template.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            as_attachment=True,
            mimetype="application/pdf",
        )
    else:
        flash(_("Generated PDF not found. Please generate it again."), "error")
        return redirect(url_for("pdf_mapper.edit_template", id=id))


@bp.route("/template/<int:id>/delete", methods=["POST"])
def delete_template(id):
    """Delete a PDF template."""
    template = PDFTemplate.query.get_or_404(id)

    # Delete the file
    try:
        pdf_path = resolve_pdf_path(template)
        if pdf_path.exists():
            pdf_path.unlink()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to delete PDF file: {e}")

    # Delete the database record
    db.session.delete(template)
    db.session.commit()

    flash(_("Template deleted successfully"), "success")
    return redirect(url_for("pdf_mapper.index"))


@bp.route("/template/<int:id>/reupload", methods=["GET", "POST"])
def reupload_template(id):
    """Re-upload a PDF file for an existing template."""
    template = PDFTemplate.query.get_or_404(id)

    if request.method == "POST":
        if "pdf_file" not in request.files:
            flash(_("No PDF file uploaded"), "error")
            return redirect(request.url)

        file = request.files["pdf_file"]
        if file.filename == "":
            flash(_("No file selected"), "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"

            # Save to data directory
            data_dir = Path("/app/data")
            upload_dir = data_dir / "pdf_templates"
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / unique_filename
            file.save(str(file_path))

            # Update template with new file path
            template.file_path = str(file_path)
            db.session.commit()

            flash(_("PDF file re-uploaded successfully"), "success")
            return redirect(url_for("pdf_mapper.index"))

    return render_template("pdf_mapper/reupload.html", template=template)


def generate_preview_pdf(template, sample_data):
    """Generate a preview PDF with sample data."""
    # Use the helper function to resolve the PDF path
    pdf_path = resolve_pdf_path(template)

    output_path = Path(tempfile.gettempdir()) / f"preview_{template.id}.pdf"

    with open(pdf_path, "rb") as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        pdf_writer = PdfWriter()

        # Get the first page
        page = pdf_reader.pages[0]

        # Apply field mappings to sample data
        if template.field_mappings and template.column_formulas:
            # Process each row of data
            for row_idx, med_data in enumerate(sample_data, 1):
                # Process each column
                for col_idx in range(1, template.columns_count + 1):
                    field_name = f"row_{row_idx}_col_{col_idx}"

                    # Get column formula
                    formula = template.column_formulas.get(str(col_idx), {})
                    if formula:
                        # Combine fields according to formula
                        field_values = []
                        for field in formula.get("fields", []):
                            value = med_data.get(field, "")
                            if value:
                                field_values.append(str(value))

                        field_value = formula.get("separator", " ").join(
                            field_values
                        )
                    else:
                        field_value = ""

                    # In a real implementation, you would set the form field value
                    # For now, we'll just add the page as-is

        pdf_writer.add_page(page)

        # Write the output
        with open(output_path, "wb") as output_file:
            pdf_writer.write(output_file)

        # Verify the output file was created and has fields
        logger.info(f"Generated PDF saved to: {output_path}")

        # Quick verification
        try:
            with open(output_path, "rb") as verify_file:
                verify_reader = PdfReader(verify_file)
                verify_fields = verify_reader.get_fields()
                if verify_fields:
                    filled_count = sum(
                        1
                        for field in verify_fields.values()
                        if field.get("/V")
                    )
                    logger.info(
                        f"Verification: PDF has {len(verify_fields)} fields, {filled_count} are filled"
                    )
                    # Log a sample of filled fields
                    sample_filled = []
                    for name, field in list(verify_fields.items())[:10]:
                        value = field.get("/V", "")
                        if value:
                            sample_filled.append(f"{name}={value}")
                    if sample_filled:
                        logger.info(
                            f"Sample filled fields: {', '.join(sample_filled[:5])}"
                        )
                else:
                    logger.warning(
                        "Verification: Generated PDF has no form fields!"
                    )
        except Exception as ve:
            logger.error(f"Error verifying generated PDF: {ve}")

    # Restore pypdf logging level
    pypdf_logger.setLevel(original_level)

    return str(output_path)


def generate_filled_pdf_from_template(template, medications):
    """Generate a filled PDF from template with actual medication data."""
    import logging

    logger = logging.getLogger(__name__)

    # Suppress pypdf font warnings since we're using NeedAppearances flag
    pypdf_logger = logging.getLogger("pypdf._writer")
    original_level = pypdf_logger.level
    pypdf_logger.setLevel(logging.ERROR)

    # Use the helper function to resolve the PDF path
    pdf_path = resolve_pdf_path(template)
    logger.info(
        f"Generating PDF from template {template.id} with {len(medications)} medications"
    )
    logger.debug(f"Template has column_formulas: {template.column_formulas}")
    logger.debug(
        f"Template has structure_mapping: {template.structure_mapping}"
    )

    output_path = (
        Path(tempfile.gettempdir())
        / f"generated_{template.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    with open(pdf_path, "rb") as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        pdf_writer = PdfWriter()

        # Check if PDF has form fields
        form_fields = pdf_reader.get_fields()
        if form_fields:
            logger.info(f"PDF has {len(form_fields)} form fields")
            field_names = list(form_fields.keys())
            logger.debug(
                f"Form field names: {field_names[:20]}..."
            )  # Log first 20 field names

            # Check if we have the expected field naming pattern
            expected_pattern = "row_"
            matching_fields = [f for f in field_names if expected_pattern in f]
            if matching_fields:
                logger.info(
                    f"Found {len(matching_fields)} fields matching pattern '{expected_pattern}'"
                )
                logger.debug(f"Matching fields: {matching_fields[:10]}")
            else:
                logger.warning(
                    f"No fields matching expected pattern '{expected_pattern}' found!"
                )
                logger.info(
                    "This might mean the PDF needs form fields created or uses a different naming pattern"
                )
        else:
            logger.warning("PDF has NO form fields detected!")

        # Prepare all field updates first
        all_field_updates = {}
        medications_processed = 0

        while medications_processed < len(medications):
            # Calculate which medications go on this page
            start_idx = medications_processed
            end_idx = min(start_idx + template.rows_per_page, len(medications))
            page_medications = medications[start_idx:end_idx]

            if not page_medications:
                break

            logger.info(f"Processing medications {start_idx + 1} to {end_idx}")

            # Process each medication
            for row_idx, med in enumerate(page_medications, 1):
                # Get product and ingredient information
                product = med.default_product or (
                    med.migrated_product[0] if med.migrated_product else None
                )

                # Calculate daily units from schedules or use daily_usage
                daily_units = med.daily_usage if med.daily_usage > 0 else 0

                # Get strength value and unit
                strength_value = ""
                strength_unit = ""
                if product and product.active_ingredient:
                    raw_strength = (
                        product.active_ingredient.strength
                        if product.active_ingredient.strength
                        else med.dosage if med.dosage else ""
                    )
                    # Validate and clean the strength value
                    strength_value = validate_and_clean_strength(raw_strength)
                    strength_unit = (
                        product.active_ingredient.strength_unit
                        if product.active_ingredient.strength_unit
                        else ""
                    )
                else:
                    # Parse from medication dosage if available
                    if med.dosage:
                        # Validate and clean the dosage value
                        strength_value = validate_and_clean_strength(med.dosage)
                    strength_unit = (
                        med.form if hasattr(med, "form") and med.form else "mg"
                    )

                # Calculate daily dosage (strength × daily units)
                daily_dosage = ""
                if strength_value and daily_units:
                    try:
                        # Handle German decimal format (1,25 -> 1.25)
                        strength_clean = str(strength_value).replace(',', '.')
                        strength_num = float(strength_clean)
                        total_dosage = strength_num * daily_units
                        # Output only the numeric value without unit
                        daily_dosage = f"{total_dosage:.2f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        # Fallback: just return the calculation string without unit
                        daily_dosage = f"{daily_units} × {strength_value}"

                # Determine dosage form
                # First try to use the form from the active ingredient
                dosage_form = ""
                if product and product.active_ingredient and product.active_ingredient.form:
                    dosage_form = product.active_ingredient.form
                elif hasattr(med, 'form') and med.form:
                    dosage_form = med.form
                else:
                    # Fallback: try to infer from unit or name
                    if strength_unit:
                        if "ml" in strength_unit.lower():
                            dosage_form = "ml"
                        elif "mg" in strength_unit.lower():
                            dosage_form = "tablets"
                    if not dosage_form:  # Still no form determined
                        if "drops" in med.name.lower():
                            dosage_form = "drops"
                        elif "spray" in med.name.lower():
                            dosage_form = "sprays"
                        else:
                            dosage_form = "tablets"  # Final default

                # Determine package size to order (prefer N2, then N3, then N1)
                package_size_ordered = "N1"
                if med.package_size_n2 and med.package_size_n2 > 0:
                    package_size_ordered = "N2"
                elif med.package_size_n3 and med.package_size_n3 > 0:
                    package_size_ordered = "N3"
                elif med.package_size_n1 and med.package_size_n1 > 0:
                    package_size_ordered = "N1"

                # Calculate packages needed based on daily usage
                packages_ordered = 1  # Default to 1 package
                if daily_units > 0:
                    # Get the quantity in the selected package size
                    if package_size_ordered == "N1":
                        units_per_package = med.package_size_n1 or 30
                    elif package_size_ordered == "N2":
                        units_per_package = med.package_size_n2 or 60
                    else:  # N3
                        units_per_package = med.package_size_n3 or 100

                    # Calculate how many packages for ~30 days supply
                    days_supply = 30
                    total_units_needed = daily_units * days_supply
                    packages_ordered = max(
                        1,
                        int(
                            (total_units_needed + units_per_package - 1)
                            / units_per_package
                        ),
                    )

                med_data = {
                    "brand_name": product.brand_name if product else med.name,
                    "manufacturer": product.manufacturer if product else "",
                    "display_name": (
                        product.display_name if product else med.name
                    ),
                    "active_ingredient": (
                        product.active_ingredient.name
                        if product and product.active_ingredient
                        else med.active_ingredient
                    ),
                    "strength": validate_and_clean_strength(
                        product.active_ingredient.strength
                        if product and product.active_ingredient
                        else med.dosage
                    ),
                    "unit": (
                        product.active_ingredient.strength_unit
                        if product and product.active_ingredient
                        else ""
                    ),
                    "package_size": "N1",  # Default
                    "quantity": med.package_size_n1 or 0,
                    "pzn": "",  # Would come from package
                    "gtin": "",  # Would come from package
                    "physician": (
                        med.physician.display_name if med.physician else ""
                    ),
                    "instructions": med.notes or "",
                    "notes": med.notes or "",
                    # Dosage fields
                    "daily_units": (
                        str(int(daily_units)) if daily_units > 0 else ""
                    ),
                    "dosage_form": dosage_form,
                    "strength_value": strength_value,
                    "strength_unit": strength_unit,
                    "daily_dosage": daily_dosage,
                    # Order fields
                    "package_size_ordered": package_size_ordered,
                    "packages_ordered": str(packages_ordered),
                }

                # Apply column formulas
                for col_idx in range(1, template.columns_count + 1):
                    # Get the actual PDF field name from structure mapping
                    mapping_key = f"{row_idx}_{col_idx}"

                    if (
                        template.structure_mapping
                        and mapping_key in template.structure_mapping
                    ):
                        # Use the actual PDF field name
                        actual_field_name = template.structure_mapping[
                            mapping_key
                        ].get("field", "")

                        # Get column formula
                        formula = template.column_formulas.get(
                            str(col_idx), {}
                        )
                        if formula and actual_field_name:
                            # Combine fields according to formula
                            field_values = []
                            for field in formula.get("fields", []):
                                value = med_data.get(field, "")
                                if value:
                                    field_values.append(str(value))

                            field_value = formula.get("separator", " ").join(
                                field_values
                            )

                            # Add to all field updates using the actual field name
                            all_field_updates[actual_field_name] = field_value
                            logger.debug(
                                f"Prepared field {actual_field_name} = {field_value[:50]}..."
                            )
                    else:
                        logger.warning(
                            f"No structure mapping found for position {row_idx}_{col_idx}"
                        )

            medications_processed = end_idx

        # Now apply all field updates to the PDF
        if all_field_updates:
            logger.info(f"Updating {len(all_field_updates)} fields in PDF")

            # Use the simplest, most reliable method
            try:
                # Add all pages from the reader
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

                # Copy the AcroForm from reader to preserve field settings
                if "/AcroForm" in pdf_reader.trailer["/Root"]:
                    pdf_writer._root_object.update(
                        {
                            NameObject("/AcroForm"): pdf_reader.trailer[
                                "/Root"
                            ]["/AcroForm"]
                        }
                    )

                # Simply update form field values - as native as possible
                for field_name, field_value in all_field_updates.items():
                    try:
                        pdf_writer.update_page_form_field_values(
                            pdf_writer.pages[0],  # Assuming single page form
                            {field_name: field_value},
                        )
                        logger.debug(
                            f"Updated field {field_name} = {field_value[:50] if field_value else ''}"
                        )
                    except Exception as field_error:
                        logger.warning(
                            f"Could not update field {field_name}: {field_error}"
                        )

                logger.info("Successfully updated form fields")

            except Exception as e:
                logger.error(f"Error updating form fields: {e}")
                logger.info("Trying alternative pypdf method")

                # Alternative: Try using the newer pypdf API
                try:
                    pdf_writer = PdfWriter()

                    # Clone the document root to preserve form structure
                    pdf_writer.clone_reader_document_root(pdf_reader)

                    # Get the fields and update them
                    if pdf_writer.get_fields():
                        for (
                            field_name,
                            field_value,
                        ) in all_field_updates.items():
                            try:
                                # Find the field in the writer
                                fields = pdf_writer.get_fields()
                                if field_name in fields:
                                    # Update using the writer's internal method
                                    pdf_writer.update_page_form_field_values(
                                        pdf_writer.pages[0],
                                        {field_name: field_value},
                                        auto_regenerate=False,  # Don't regenerate appearance
                                    )
                                    logger.debug(
                                        f"Updated field {field_name} via clone method"
                                    )
                            except Exception as fe:
                                logger.warning(
                                    f"Field {field_name} update failed: {fe}"
                                )

                    logger.info("Updated fields using clone method")

                except Exception as e2:
                    logger.error(f"Both methods failed: {e}, {e2}")
                    logger.warning("Generating PDF without form field updates")
                    # If all methods fail, just copy pages
                    pdf_writer = PdfWriter()
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
        else:
            # No fields to update, just copy pages
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)

        # Write the output
        with open(output_path, "wb") as output_file:
            pdf_writer.write(output_file)

        # Verify the output file was created and has fields
        logger.info(f"Generated PDF saved to: {output_path}")

        # Quick verification
        try:
            with open(output_path, "rb") as verify_file:
                verify_reader = PdfReader(verify_file)
                verify_fields = verify_reader.get_fields()
                if verify_fields:
                    filled_count = sum(
                        1
                        for field in verify_fields.values()
                        if field.get("/V")
                    )
                    logger.info(
                        f"Verification: PDF has {len(verify_fields)} fields, {filled_count} are filled"
                    )
                    # Log a sample of filled fields
                    sample_filled = []
                    for name, field in list(verify_fields.items())[:10]:
                        value = field.get("/V", "")
                        if value:
                            sample_filled.append(f"{name}={value}")
                    if sample_filled:
                        logger.info(
                            f"Sample filled fields: {', '.join(sample_filled[:5])}"
                        )
                else:
                    logger.warning(
                        "Verification: Generated PDF has no form fields!"
                    )
        except Exception as ve:
            logger.error(f"Error verifying generated PDF: {ve}")

    # Restore pypdf logging level
    pypdf_logger.setLevel(original_level)

    return str(output_path)


@bp.route("/template/<int:id>/export")
def export_template_config(id):
    """Export template configuration as JSON."""
    template = PDFTemplate.query.get_or_404(id)

    config = {
        "name": template.name,
        "description": template.description,
        "rows_per_page": template.rows_per_page,
        "columns_count": template.columns_count,
        "structure_mapping": template.structure_mapping,
        "column_formulas": template.column_formulas,
        "table_config": template.table_config,
    }

    return jsonify({"success": True, "config": config})


@bp.route("/template/<int:id>/import", methods=["POST"])
def import_template_config(id):
    """Import template configuration from JSON."""
    template = PDFTemplate.query.get_or_404(id)

    try:
        config = request.get_json()

        # Update template with imported configuration
        if "rows_per_page" in config:
            template.rows_per_page = config["rows_per_page"]
        if "columns_count" in config:
            template.columns_count = config["columns_count"]
        if "structure_mapping" in config:
            template.structure_mapping = config["structure_mapping"]
        if "column_formulas" in config:
            template.column_formulas = config["column_formulas"]
        if "table_config" in config:
            template.table_config = config["table_config"]

        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/template/<int:id>/delete", methods=["POST"])
def delete_template_api(id):
    """Delete template via API."""
    template = PDFTemplate.query.get_or_404(id)

    try:
        # Delete the PDF file if it exists
        if template.file_path and os.path.exists(template.file_path):
            os.remove(template.file_path)

        db.session.delete(template)
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
