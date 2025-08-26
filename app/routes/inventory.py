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
from flask_babel import gettext as _

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
    """Display inventory overview for all medications grouped by physician."""
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
        "inventory/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medications_by_physician=medications_by_physician,
        sorted_physicians=sorted_physicians,
        otc_medications=otc_medications,
    )


@inventory_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display detailed inventory information for a specific medication."""
    from models import PackageInventory, ScannedItem
    
    inventory = Inventory.query.get_or_404(id)
    logs = (
        InventoryLog.query.filter_by(inventory_id=id)
        .order_by(InventoryLog.timestamp.desc())
        .limit(10)
        .all()
    )
    
    # Get package inventory for this medication
    from models import MedicationPackage, ActiveIngredient, MedicationProduct, ProductPackage
    
    # First get packages with direct medication_id link (old system)
    old_package_inventory = (
        db.session.query(PackageInventory, ScannedItem, MedicationPackage)
        .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
        .outerjoin(MedicationPackage, ScannedItem.medication_package_id == MedicationPackage.id)
        .filter(PackageInventory.medication_id == inventory.medication_id)
        .filter(PackageInventory.status.in_(['sealed', 'open', 'empty']))  # Include empty packages
        .order_by(ScannedItem.expiry_date.asc())
        .all()
    )
    
    # Now get packages for the same active ingredient (new system)
    # Find the active ingredient for this medication
    medication_name = inventory.medication.name
    active_ingredient = ActiveIngredient.query.filter_by(name=medication_name).first()
    
    new_package_inventory = []
    if active_ingredient:
        # Get all products for this active ingredient
        products = MedicationProduct.query.filter_by(active_ingredient_id=active_ingredient.id).all()
        product_ids = [p.id for p in products]
        
        if product_ids:
            # Get all packages for these products
            packages = ProductPackage.query.filter(ProductPackage.product_id.in_(product_ids)).all()
            package_gtins = [p.gtin for p in packages if p.gtin]
            
            if package_gtins:
                # Get inventory for packages with matching GTINs and no medication_id
                new_package_inventory_raw = (
                    db.session.query(PackageInventory, ScannedItem)
                    .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
                    .filter(PackageInventory.medication_id == None)  # Only new system packages
                    .filter(ScannedItem.gtin.in_(package_gtins))
                    .filter(PackageInventory.status.in_(['sealed', 'open', 'empty']))
                    .order_by(ScannedItem.expiry_date.asc())
                    .all()
                )
                
                # For each new package, create a mock MedicationPackage or fetch the ProductPackage info
                for pkg_inv, scanned in new_package_inventory_raw:
                    # Find the matching ProductPackage
                    matching_package = ProductPackage.query.filter_by(gtin=scanned.gtin).first()
                    
                    # Create a mock MedicationPackage object with package_size for display
                    if matching_package:
                        # Create a simple object to hold the package size for display
                        class PackageInfo:
                            def __init__(self, package_size, quantity):
                                self.package_size = package_size
                                self.quantity = quantity
                        
                        package_info = PackageInfo(
                            package_size=matching_package.package_size or 'N/A',
                            quantity=matching_package.quantity
                        )
                        new_package_inventory.append((pkg_inv, scanned, package_info))
                    else:
                        new_package_inventory.append((pkg_inv, scanned, None))
    
    # Combine both old and new package inventories
    package_inventory = old_package_inventory + new_package_inventory
    
    # Calculate total units from packages
    package_units = sum(pkg.current_units for pkg, _, _ in package_inventory)

    from datetime import date
    
    return render_template(
        "inventory/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        inventory=inventory,
        medication=inventory.medication,
        logs=logs,
        package_inventory=package_inventory,
        package_units=package_units,
        total_units=inventory.current_count + package_units,
        today=date.today()
    )


@inventory_bp.route("/<int:id>/manual_deduct", methods=["POST"])
def manual_deduct(id: int):
    """
    Manually deduct units from inventory (for on-demand medications or extra doses).
    Uses the same intelligent deduction system as automatic deductions.
    """
    # Get medication by ID (the form sends medication.id, not inventory.id)
    medication = Medication.query.get_or_404(id)
    
    # Ensure the medication has an inventory record
    if not medication.inventory:
        flash(_("No inventory record found for this medication"), "error")
        return redirect(url_for("inventory.index"))
    
    # Get the amount to deduct from form
    # Handle both comma and dot as decimal separator (for German locale)
    amount_str = request.form.get("amount", "0")
    amount_str = amount_str.replace(",", ".")
    try:
        amount = int(float(amount_str))
    except (ValueError, TypeError):
        amount = 0
    notes = request.form.get("notes", "").strip()
    
    if amount <= 0:
        flash(_("Please enter a valid amount to deduct"), "error")
        return redirect(url_for("inventory.show", id=medication.inventory.id))
    
    # Check if enough inventory available
    if medication.total_inventory_count < amount:
        flash(
            _("Not enough inventory. Available: %(available)s units, Requested: %(requested)s units", 
              available=medication.total_inventory_count, requested=amount),
            "error"
        )
        return redirect(url_for("inventory.show", id=medication.inventory.id))
    
    # Use the same intelligent deduction method as automatic deductions
    result = medication.deduct_units(
        amount,
        f"Manual deduction: {notes if notes else f'{amount} units taken manually'}"
    )
    
    if result['success']:
        db.session.commit()
        
        # Build success message
        msg = _("Successfully deducted %(amount)s units", amount=amount)
        
        if result['legacy_deducted'] > 0:
            msg += f" ({result['legacy_deducted']} {_('from legacy')})"
        
        if result['packages_deducted']:
            pkg_count = len(result['packages_deducted'])
            msg += f" ({pkg_count} {_('package') if pkg_count == 1 else _('packages')} {_('used')})"
        
        flash(msg, "success")
    else:
        flash(
            _("Failed to deduct units: %(reason)s", 
              reason="; ".join(result['notes'])),
            "error"
        )
    
    return redirect(url_for("inventory.show", id=medication.inventory.id))

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
        _("Inventory for {} adjusted by {}").format(inventory.medication.name, adjustment), "success"
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

    flash(_("Inventory updated for {}").format(inventory.medication.name), "success")
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


@inventory_bp.route("/package/<int:package_id>/edit", methods=["GET", "POST"])
def edit_package(package_id: int):
    """Edit a scanned package inventory item."""
    from models import PackageInventory, ScannedItem
    
    package = PackageInventory.query.get_or_404(package_id)
    scanned_item = package.scanned_item
    
    if request.method == "POST":
        # Update batch, expiry, and serial for non-GS1 items
        if scanned_item and not scanned_item.is_gs1:
            # Update serial number if provided
            serial_number = request.form.get("serial_number", "").strip()
            if serial_number and serial_number != scanned_item.serial_number:
                # Check if new serial number already exists
                from models import ScannedItem as SI
                existing = SI.query.filter_by(serial_number=serial_number).first()
                if existing and existing.id != scanned_item.id:
                    flash(_("Serial number already exists for another package"), "error")
                else:
                    scanned_item.serial_number = serial_number
            
            # Update batch number if provided
            batch_number = request.form.get("batch_number", "").strip()
            if batch_number != (scanned_item.batch_number or ""):
                scanned_item.batch_number = batch_number if batch_number else None
            
            # Update expiry date if provided
            expiry_date_str = request.form.get("expiry_date", "").strip()
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                    scanned_item.expiry_date = expiry_date
                except ValueError:
                    flash(_("Invalid expiry date format"), "warning")
            elif scanned_item.expiry_date:
                # Clear expiry date if field was emptied
                scanned_item.expiry_date = None
        
        # Update package status
        new_status = request.form.get("status")
        if new_status in ["sealed", "open", "empty", "discarded"]:
            package.status = new_status
        
        # Update order association
        order_item_id = request.form.get("order_item_id")
        if order_item_id:
            package.order_item_id = int(order_item_id) if order_item_id else None
        else:
            package.order_item_id = None
        
        # Update current units and track the change
        current_units = request.form.get("current_units")
        if current_units:
            try:
                # Store the old value to calculate adjustment
                old_units = package.current_units
                new_units = int(current_units)
                
                if 0 <= new_units <= package.original_units:
                    package.current_units = new_units
                    
                    # Auto-update status based on units
                    if new_units == 0:
                        package.status = "empty"
                    elif new_units < package.original_units and package.status == "sealed":
                        package.status = "open"
                    
                    # Create inventory log if units changed
                    adjustment = new_units - old_units
                    if adjustment != 0:
                        inventory = Inventory.query.filter_by(medication_id=package.medication_id).first()
                        if inventory:
                            # Get notes from form or create default message
                            notes = request.form.get("notes", "").strip()
                            if not notes:
                                notes = f"Package adjustment (Serial: {scanned_item.serial_number})"
                            else:
                                notes = f"Package {scanned_item.serial_number}: {notes}"
                            
                            # Update the legacy inventory count to reflect package change
                            # Note: We're just logging the change, not updating legacy inventory
                            # since packages are tracked separately
                            from models import InventoryLog
                            
                            # Calculate what the total inventory would be with this change
                            medication = package.medication
                            total_before = medication.total_inventory_count - adjustment
                            total_after = medication.total_inventory_count
                            
                            log = InventoryLog(
                                inventory_id=inventory.id,
                                previous_count=total_before,
                                adjustment=adjustment,
                                new_count=total_after,
                                notes=notes
                            )
                            db.session.add(log)
                else:
                    flash(_("Units must be between 0 and %(max)s", max=package.original_units), "error")
                    return redirect(url_for("inventory.edit_package", package_id=package_id))
            except ValueError:
                flash(_("Invalid units value"), "error")
                return redirect(url_for("inventory.edit_package", package_id=package_id))
        
        db.session.commit()
        flash(_("Package updated successfully"), "success")
        
        # Return to inventory show page
        inventory = Inventory.query.filter_by(medication_id=package.medication_id).first()
        if inventory:
            return redirect(url_for("inventory.show", id=inventory.id))
        else:
            return redirect(url_for("inventory.index"))
    
    # GET request - show edit form
    inventory = Inventory.query.filter_by(medication_id=package.medication_id).first()
    
    # Get order items for this medication
    from models import Order, OrderItem
    
    pending_order_items = (
        OrderItem.query.join(Order)
        .filter(
            OrderItem.medication_id == package.medication_id,
            OrderItem.fulfillment_status == 'pending',
            Order.status.in_(['planned', 'printed'])
        )
        .order_by(Order.created_date.desc())
        .all()
    )
    
    fulfilled_order_items = (
        OrderItem.query.join(Order)
        .filter(
            OrderItem.medication_id == package.medication_id,
            OrderItem.fulfillment_status.in_(['fulfilled', 'partial'])
        )
        .order_by(Order.created_date.desc())
        .limit(10)
        .all()
    )
    
    from datetime import date
    
    return render_template(
        "inventory/edit_package.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        package=package,
        scanned_item=scanned_item,
        medication=package.medication,
        inventory=inventory,
        pending_order_items=pending_order_items,
        fulfilled_order_items=fulfilled_order_items,
        today=date.today()
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
