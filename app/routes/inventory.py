"""
Routes for inventory management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

# Local application imports
from models import (
    Inventory,
    InventoryLog,
    Medication,
    db,
)
from utils import to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for inventory routes
inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
def index():
    """Display inventory overview for all medications."""
    medications = Medication.query.all()
    return render_template(
        "inventory/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medications=medications,
    )


@inventory_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display detailed inventory information for a specific medication."""
    inventory = Inventory.query.get_or_404(id)
    logs = (
        InventoryLog.query.filter_by(inventory_id=id)
        .order_by(InventoryLog.timestamp.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "inventory/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        inventory=inventory,
        medication=inventory.medication,
        logs=logs,
    )


@inventory_bp.route("/<int:id>/adjust", methods=["POST"])
def adjust(id: int):
    """Adjust inventory level for a medication."""
    inventory = Inventory.query.get_or_404(id)

    # Extract form data
    direct_adjustment = request.form.get("adjustment", "")
    notes = request.form.get("notes", "")
    referer = request.form.get("referer", None)
    
    # Get package adjustment data
    adj_packages_n1 = int(request.form.get("adj_packages_n1", 0) or 0)
    adj_packages_n2 = int(request.form.get("adj_packages_n2", 0) or 0)
    adj_packages_n3 = int(request.form.get("adj_packages_n3", 0) or 0)

    # Calculate the total adjustment
    if direct_adjustment.strip():
        # Use direct adjustment if provided
        adjustment = int(direct_adjustment)
    else:
        # Calculate from package quantities
        medication = inventory.medication
        package_adjustment = (
            adj_packages_n1 * (medication.package_size_n1 or 0) +
            adj_packages_n2 * (medication.package_size_n2 or 0) +
            adj_packages_n3 * (medication.package_size_n3 or 0)
        )
        adjustment = package_adjustment

    # Update inventory
    inventory.update_count(adjustment, notes)
    db.session.commit()

    flash(
        f"Inventory for {inventory.medication.name} adjusted by {adjustment}", "success"
    )

    # Check if referer is provided
    if referer == "index":
        return redirect(url_for("inventory.index"))
    else:
        return redirect(url_for("inventory.show", id=inventory.id))


@inventory_bp.route("/<int:id>/update_packages", methods=["POST"])
def update_packages(id: int):
    """Update inventory based on package counts or direct unit entry."""
    inventory = Inventory.query.get_or_404(id)

    # Extract form data
    direct_units = request.form.get("direct_units", "")

    # Calculate previous total
    previous_total = inventory.current_count

    # Check if direct units input was provided
    if direct_units and direct_units.strip():
        # Set the current_count directly
        inventory.current_count = int(direct_units)

        # Update package counts based on the new total
        # This is a simplified calculation - it won't be perfectly accurate but provides an estimate
        remaining = inventory.current_count

        if inventory.medication.package_size_n3:
            inventory.packages_n3 = remaining // inventory.medication.package_size_n3
            remaining %= inventory.medication.package_size_n3

        if inventory.medication.package_size_n2:
            inventory.packages_n2 = remaining // inventory.medication.package_size_n2
            remaining %= inventory.medication.package_size_n2

        if inventory.medication.package_size_n1:
            inventory.packages_n1 = remaining // inventory.medication.package_size_n1

        notes = f"Set directly to {inventory.current_count} units"
    else:
        # Use package counts as before
        packages_n1 = int(request.form.get("packages_n1", 0) or 0)
        packages_n2 = int(request.form.get("packages_n2", 0) or 0)
        packages_n3 = int(request.form.get("packages_n3", 0) or 0)

        # Update package counts
        inventory.packages_n1 = packages_n1
        inventory.packages_n2 = packages_n2
        inventory.packages_n3 = packages_n3

        # Update pill count based on packages
        inventory.update_from_packages()

        notes = f"Updated from package counts: N1={packages_n1}, N2={packages_n2}, N3={packages_n3}"

    # Create log entry for the change
    adjustment = inventory.current_count - previous_total
    log = InventoryLog(
        inventory_id=inventory.id,
        previous_count=previous_total,
        adjustment=adjustment,
        new_count=inventory.current_count,
        notes=notes,
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Inventory updated for {inventory.medication.name}", "success")
    return redirect(url_for("inventory.show", id=inventory.id))


@inventory_bp.route("/<int:id>/logs")
def logs(id: int):
    """Display complete inventory history for a medication."""
    inventory = Inventory.query.get_or_404(id)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    logs = (
        InventoryLog.query.filter_by(inventory_id=id)
        .order_by(InventoryLog.timestamp.desc())
        .paginate(page=page, per_page=per_page)
    )

    return render_template(
        "inventory/logs.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        inventory=inventory,
        medication=inventory.medication,
        logs=logs,
    )


@inventory_bp.route("/low")
def low():
    """Display medications with inventory below threshold."""
    low_inventory = []
    medications = Medication.query.all()

    for med in medications:
        if med.inventory and med.inventory.is_low:
            low_inventory.append(med)

    return render_template(
        "inventory/low.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medications=low_inventory,
    )


@inventory_bp.route("/depletion")
def depletion():
    """Display projected depletion dates for all medications."""
    medications = Medication.query.all()

    # Sort by depletion date
    medications_with_dates = [m for m in medications if m.depletion_date is not None]
    medications_with_dates.sort(key=lambda m: m.depletion_date)

    medications_without_dates = [m for m in medications if m.depletion_date is None]

    return render_template(
        "inventory/depletion.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medications_with_dates=medications_with_dates,
        medications_without_dates=medications_without_dates,
    )
