"""
Routes for medication management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext as _

# Local application imports
from models import (
    Inventory,
    Medication,
    Physician,
    db,
)
from utils import to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for medication routes
medication_bp = Blueprint("medications", __name__, url_prefix="/medications")


@medication_bp.route("/")
def index():
    """Display list of all medications grouped by physician."""
    medications = Medication.query.order_by(Medication.name).all()
    
    # Group medications by physician or OTC status
    medications_by_physician = {}
    otc_medications = []
    
    for med in medications:
        if med.is_otc:
            otc_medications.append(med)
        else:
            physician_key = med.physician if med.physician else None
            if physician_key not in medications_by_physician:
                medications_by_physician[physician_key] = []
            medications_by_physician[physician_key].append(med)
    
    # Sort physicians by name, with unassigned at the end
    sorted_physicians = sorted(
        medications_by_physician.keys(),
        key=lambda p: (p is None, p.name if p else "")
    )
    
    return render_template(
        "medications/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medications_by_physician=medications_by_physician,
        sorted_physicians=sorted_physicians,
        otc_medications=otc_medications,
    )


@medication_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new medication."""
    if request.method == "POST":
        # Extract form data
        name = request.form.get("name", "")
        notes = request.form.get("notes", "")

        # Extract new fields for prescription form
        active_ingredient = request.form.get("active_ingredient", "")
        form = request.form.get("form", "")

        # Keep these fields for database compatibility, but they're no longer used for calculations
        dosage = float(request.form.get("dosage", 1))  # Default to 1
        frequency = float(request.form.get("frequency", 1))  # Default to 1

        package_size_n1 = int(request.form.get("package_size_n1", 0) or 0)
        package_size_n2 = int(request.form.get("package_size_n2", 0) or 0)
        package_size_n3 = int(request.form.get("package_size_n3", 0) or 0)

        min_threshold = int(request.form.get("min_threshold", 0) or 0)
        safety_margin_days = int(request.form.get("safety_margin_days", 30) or 30)

        # Extract new physician and OTC fields
        is_otc = bool(request.form.get("is_otc"))
        
        # If OTC, always clear physician
        if is_otc:
            physician_id = None
        else:
            physician_id = request.form.get("physician_id")
            if physician_id == "":
                physician_id = None
            elif physician_id:
                physician_id = int(physician_id)

        aut_idem = bool(request.form.get("aut_idem"))

        # Create new medication
        medication = Medication(
            name=name,
            physician_id=physician_id,
            is_otc=is_otc,
            aut_idem=aut_idem,
            active_ingredient=active_ingredient,
            form=form,
            dosage=dosage,  # Kept for database compatibility
            frequency=frequency,  # Kept for database compatibility
            notes=notes,
            package_size_n1=package_size_n1,
            package_size_n2=package_size_n2,
            package_size_n3=package_size_n3,
            min_threshold=min_threshold,
            safety_margin_days=safety_margin_days,
        )

        # Create inventory record
        inventory = Inventory(medication=medication, current_count=0)

        db.session.add(medication)
        db.session.add(inventory)
        db.session.commit()

        flash(_("Medication '{}' added successfully").format(name), "success")

        # Redirect to scheduling page instead of index
        return redirect(url_for("schedules.new", medication_id=medication.id))

    physicians = Physician.query.order_by(Physician.name).all()
    return render_template("medications/new.html", physicians=physicians)


@medication_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific medication."""
    medication = Medication.query.get_or_404(id)
    return render_template(
        "medications/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medication=medication,
    )


@medication_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing medication."""
    medication = Medication.query.get_or_404(id)

    if request.method == "POST":
        # Update medication with form data
        medication.name = request.form.get("name", medication.name)

        # Update new fields for prescription form
        medication.active_ingredient = request.form.get("active_ingredient", "")
        medication.form = request.form.get("form", "")

        # Keep these fields for database compatibility, but they're no longer used for calculations
        medication.dosage = float(request.form.get("dosage", medication.dosage))
        medication.frequency = float(
            request.form.get("frequency", medication.frequency)
        )

        medication.notes = request.form.get("notes", medication.notes)

        medication.package_size_n1 = int(
            request.form.get("package_size_n1", medication.package_size_n1) or 0
        )
        medication.package_size_n2 = int(
            request.form.get("package_size_n2", medication.package_size_n2) or 0
        )
        medication.package_size_n3 = int(
            request.form.get("package_size_n3", medication.package_size_n3) or 0
        )

        medication.min_threshold = int(
            request.form.get("min_threshold", medication.min_threshold) or 0
        )
        medication.safety_margin_days = int(
            request.form.get("safety_margin_days", medication.safety_margin_days) or 30
        )

        # Update physician and OTC fields
        medication.is_otc = bool(request.form.get("is_otc"))
        
        # If OTC, always clear physician
        if medication.is_otc:
            medication.physician_id = None
        else:
            physician_id = request.form.get("physician_id")
            if physician_id == "":
                medication.physician_id = None
            elif physician_id:
                medication.physician_id = int(physician_id)
        
        medication.aut_idem = bool(request.form.get("aut_idem"))

        db.session.commit()

        flash(_("Medication '{}' updated successfully").format(medication.name), "success")

        # If medication has no schedules, redirect to scheduling page
        if not medication.schedules:
            return redirect(url_for("schedules.new", medication_id=medication.id))
        else:
            return redirect(url_for("medications.show", id=medication.id))

    physicians = Physician.query.order_by(Physician.name).all()
    return render_template(
        "medications/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medication=medication,
        physicians=physicians,
    )


@medication_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a medication."""
    medication = Medication.query.get_or_404(id)

    # Check if can be deleted (e.g., no active orders)
    if medication.order_items:
        flash(
            _("Cannot delete '{}' because it has associated orders").format(medication.name),
            "error",
        )
        return redirect(url_for("medications.show", id=medication.id))

    # Delete associated inventory
    if medication.inventory:
        db.session.delete(medication.inventory)

    db.session.delete(medication)
    db.session.commit()

    flash(_("Medication '{}' deleted successfully").format(medication.name), "success")
    return redirect(url_for("medications.index"))


@medication_bp.route("/<int:id>/calculate", methods=["POST"])
def calculate_needs(id: int):
    """Calculate medication needs until next visit."""
    medication = Medication.query.get_or_404(id)

    # Get form data
    days = int(request.form.get("days", 0))
    units = int(request.form.get("units", 0) or 0)
    calculation = str(request.form.get("calculation", "total"))

    current_inventory = medication.total_inventory_count

    if days and not units:
        # Calculate needs based on days
        requested_units = int(medication.daily_usage * days)
    else:
        # Use directly provided units
        requested_units = units

    # Calculate additional units needed based on the calculation type
    if calculation == "additional":
        # Calculate additional units needed
        needed_units = requested_units + current_inventory
        additional_needed = max(0, requested_units)
    else:
        # Default to total calculation
        needed_units = requested_units
        additional_needed = max(0, needed_units - current_inventory)

    # Calculate packages
    packages = medication.calculate_packages_needed(additional_needed)

    return jsonify(
        {
            "needed_units": needed_units,
            "current_inventory": current_inventory,
            "additional_needed": additional_needed,
            "packages": packages,
        }
    )
