"""
Routes for medication management.
"""

from typing import Dict, Any, Optional, List
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from models import db, Medication, Inventory

medication_bp = Blueprint("medications", __name__, url_prefix="/medications")


@medication_bp.route("/")
def index():
    """Display list of all medications."""
    medications = Medication.query.all()
    return render_template("medications/index.html", medications=medications)


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

        # Create new medication
        medication = Medication(
            name=name,
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

        flash(f"Medication '{name}' added successfully", "success")

        # Redirect to scheduling page instead of index
        return redirect(url_for("schedules.new", medication_id=medication.id))

    return render_template("medications/new.html")


@medication_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific medication."""
    medication = Medication.query.get_or_404(id)
    return render_template("medications/show.html", medication=medication)


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

        db.session.commit()

        flash(f"Medication '{medication.name}' updated successfully", "success")

        # If medication has no schedules, redirect to scheduling page
        if not medication.schedules:
            return redirect(url_for("schedules.new", medication_id=medication.id))
        else:
            return redirect(url_for("medications.show", id=medication.id))

    return render_template("medications/edit.html", medication=medication)


@medication_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a medication."""
    medication = Medication.query.get_or_404(id)

    # Check if can be deleted (e.g., no active orders)
    if medication.order_items:
        flash(
            f"Cannot delete '{medication.name}' because it has associated orders",
            "error",
        )
        return redirect(url_for("medications.show", id=medication.id))

    # Delete associated inventory
    if medication.inventory:
        db.session.delete(medication.inventory)

    db.session.delete(medication)
    db.session.commit()

    flash(f"Medication '{medication.name}' deleted successfully", "success")
    return redirect(url_for("medications.index"))


@medication_bp.route("/<int:id>/calculate", methods=["POST"])
def calculate_needs(id: int):
    """Calculate medication needs until next visit."""
    medication = Medication.query.get_or_404(id)

    # Get form data
    days = int(request.form.get("days", 0))
    units = int(request.form.get("units", 0) or 0)

    if days and not units:
        # Calculate needs based on days
        needed_units = int(medication.daily_usage * days)
    else:
        # Use directly provided units
        needed_units = units

    current_inventory = (
        medication.inventory.current_count if medication.inventory else 0
    )

    # Calculate additional units needed
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
