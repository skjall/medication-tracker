"""
Routes for prescription template management.
"""

# Standard library imports
import json
import logging
import os
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _
from werkzeug.utils import secure_filename

# Local application imports
from models import (
    PrescriptionTemplate,
    db,
)
from utils import to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create the blueprint for prescription routes
prescription_bp = Blueprint("prescriptions", __name__, url_prefix="/prescriptions")


@prescription_bp.route("/")
def index():
    """Display list of all prescription templates."""
    templates = PrescriptionTemplate.query.all()
    active_template = PrescriptionTemplate.get_active_template()

    return render_template(
        "prescriptions/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        templates=templates,
        active_template=active_template,
    )


@prescription_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new prescription template."""
    if request.method == "POST":
        # Check if the post request has the file part
        if "template_file" not in request.files:
            flash(_("No file part"), "error")
            return redirect(url_for("prescriptions.new"))

        file = request.files["template_file"]

        # If user does not select file, browser may submit an empty file
        if file.filename == "":
            flash(_("No selected file"), "error")
            return redirect(url_for("prescriptions.new"))

        # Check if the file is a PDF
        if not file.filename.lower().endswith(".pdf"):
            flash(_("Only PDF files are allowed"), "error")
            return redirect(url_for("prescriptions.new"))

        # Extract form data
        name = request.form.get("name", "")
        description = request.form.get("description", "")
        first_field_tab_index = int(request.form.get("first_field_tab_index", 1))
        medications_per_page = int(request.form.get("medications_per_page", 15))

        # Process column mappings
        column_mappings = {}
        for i in range(1, 8):  # Process up to 7 columns
            column_num = request.form.get(f"column_{i}_num")
            column_field = request.form.get(f"column_{i}_field")

            if column_num and column_field:
                column_mappings[column_num] = column_field

        # Save the file
        templates_dir = os.path.join(current_app.root_path, "data", "templates")
        os.makedirs(templates_dir, exist_ok=True)

        # Secure the filename
        secure_name = secure_filename(file.filename)

        # Create a unique filename based on timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{secure_name}"

        file_path = os.path.join(templates_dir, filename)
        file.save(file_path)

        # Create template record
        template = PrescriptionTemplate(
            name=name,
            description=description,
            template_file=filename,
            first_field_tab_index=first_field_tab_index,
            medications_per_page=medications_per_page,
            column_mappings=json.dumps(column_mappings),
            is_active=False,
        )

        db.session.add(template)
        db.session.commit()

        flash(_("Prescription template '{}' added successfully").format(name), "success")
        return redirect(url_for("prescriptions.index"))

    # Get available field mappings for the dropdown
    field_mappings = [
        {"value": "medication_name", "label": "Medication Name"},
        {"value": "active_ingredient", "label": "Active Ingredient (Wirkstoff)"},
        {"value": "form", "label": "Form"},
        {"value": "dosage", "label": "Dosage"},
        {"value": "frequency", "label": "Frequency"},
        {"value": "daily_usage", "label": "Daily Usage"},
        {"value": "package_size_n1", "label": "Package Size N1"},
        {"value": "package_size_n2", "label": "Package Size N2"},
        {"value": "package_size_n3", "label": "Package Size N3"},
        {"value": "quantity_needed", "label": "Quantity Needed"},
        {"value": "packages_n1", "label": "Packages N1"},
        {"value": "packages_n2", "label": "Packages N2"},
        {"value": "packages_n3", "label": "Packages N3"},
    ]

    return render_template(
        "prescriptions/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        field_mappings=field_mappings,
    )


@prescription_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific prescription template."""
    template = PrescriptionTemplate.query.get_or_404(id)
    column_mappings = template.column_mapping_dict

    # Map field names to labels
    field_labels = {
        "medication_name": "Medication Name",
        "active_ingredient": "Active Ingredient (Wirkstoff)",
        "form": "Form",
        "dosage": "Dosage",
        "frequency": "Frequency",
        "daily_usage": "Daily Usage",
        "package_size_n1": "Package Size N1",
        "package_size_n2": "Package Size N2",
        "package_size_n3": "Package Size N3",
        "quantity_needed": "Quantity Needed",
        "packages_n1": "Packages N1",
        "packages_n2": "Packages N2",
        "packages_n3": "Packages N3",
    }

    return render_template(
        "prescriptions/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        template=template,
        column_mappings=column_mappings,
        field_labels=field_labels,
    )


@prescription_bp.route("/<int:id>/activate", methods=["POST"])
def activate(id: int):
    """Activate a prescription template."""
    template = PrescriptionTemplate.query.get_or_404(id)
    template.activate()

    flash(_("Prescription template '{}' activated").format(template.name), "success")
    return redirect(url_for("prescriptions.index"))


@prescription_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a prescription template."""
    template = PrescriptionTemplate.query.get_or_404(id)

    # If this is the active template, we can't delete it
    if template.is_active:
        flash(_("Cannot delete the active template"), "error")
        return redirect(url_for("prescriptions.index"))

    # Delete the template file
    try:
        file_path = os.path.join(
            current_app.root_path, "data", "templates", template.template_file
        )
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Error deleting template file: {e}")
        # Continue with deletion even if file delete fails

    # Delete the template record
    db.session.delete(template)
    db.session.commit()

    flash(_("Prescription template '{}' deleted").format(template.name), "success")
    return redirect(url_for("prescriptions.index"))


@prescription_bp.route("/<int:id>/download", methods=["GET"])
def download(id: int):
    """Download the template file."""
    template = PrescriptionTemplate.query.get_or_404(id)

    try:
        return send_file(
            template.template_path,
            download_name=template.template_file,
            as_attachment=True,
        )
    except Exception as e:
        logger.error(f"Error downloading template file: {e}")
        flash(_("Error downloading template file"), "error")
        return redirect(url_for("prescriptions.show", id=id))


@prescription_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing prescription template."""
    template = PrescriptionTemplate.query.get_or_404(id)

    if request.method == "POST":
        # Extract form data
        name = request.form.get("name", "")
        description = request.form.get("description", "")
        first_field_tab_index = int(request.form.get("first_field_tab_index", 1))
        medications_per_page = int(request.form.get("medications_per_page", 15))

        # Update the basic information
        template.name = name
        template.description = description
        template.first_field_tab_index = first_field_tab_index
        template.medications_per_page = medications_per_page

        # Process column mappings
        column_mappings = {}
        for i in range(1, 20):  # Process up to 20 columns (arbitrary limit)
            column_num = request.form.get(f"column_{i}_num")
            column_field = request.form.get(f"column_{i}_field")

            if column_num and column_field:
                column_mappings[column_num] = column_field

        # Update column mappings
        template.column_mappings = json.dumps(column_mappings)

        # Check if a new file has been uploaded
        if "template_file" in request.files and request.files["template_file"].filename:
            file = request.files["template_file"]

            # Check if the file is a PDF
            if not file.filename.lower().endswith(".pdf"):
                flash(_("Only PDF files are allowed"), "error")
                return redirect(url_for("prescriptions.edit", id=id))

            # Delete the old file
            try:
                old_file_path = os.path.join(
                    current_app.root_path, "data", "templates", template.template_file
                )
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                logger.error(f"Error deleting old template file: {e}")
                # Continue even if delete fails

            # Save the new file
            templates_dir = os.path.join(current_app.root_path, "data", "templates")

            # Secure the filename
            secure_name = secure_filename(file.filename)

            # Create a unique filename based on timestamp
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{secure_name}"

            file_path = os.path.join(templates_dir, filename)
            file.save(file_path)

            # Update the template record with new filename
            template.template_file = filename

        # Save changes
        db.session.commit()

        flash(_("Prescription template '{}' updated successfully").format(name), "success")
        return redirect(url_for("prescriptions.show", id=template.id))

    # Get available field mappings for the dropdown
    field_mappings = [
        {"value": "medication_name", "label": "Medication Name"},
        {"value": "active_ingredient", "label": "Active Ingredient (Wirkstoff)"},
        {"value": "form", "label": "Form"},
        {"value": "dosage", "label": "Dosage"},
        {"value": "frequency", "label": "Frequency"},
        {"value": "daily_usage", "label": "Daily Usage"},
        {"value": "package_size_n1", "label": "Package Size N1"},
        {"value": "package_size_n2", "label": "Package Size N2"},
        {"value": "package_size_n3", "label": "Package Size N3"},
        {"value": "quantity_needed", "label": "Quantity Needed"},
        {"value": "packages_n1", "label": "Packages N1"},
        {"value": "packages_n2", "label": "Packages N2"},
        {"value": "packages_n3", "label": "Packages N3"},
    ]

    return render_template(
        "prescriptions/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        template=template,
        field_mappings=field_mappings,
    )
