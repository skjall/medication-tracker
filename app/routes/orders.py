"""
Routes for medication order management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _

# Local application imports
from models import (
    PhysicianVisit,
    Medication,
    Order,
    OrderItem,
    db,
)
from pdf_utils import generate_prescription_pdf
from utils import to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)


# Create a blueprint for order routes
order_bp = Blueprint("orders", __name__, url_prefix="/orders")


@order_bp.route("/")
def index():
    """Display list of all medication orders."""
    # Get planned/pending orders
    pending_orders = (
        Order.query.filter(Order.status.in_(["planned", "partial"]))
        .order_by(Order.created_date.desc())
        .all()
    )

    # Get fulfilled orders
    fulfilled_orders = (
        Order.query.filter_by(status="fulfilled")
        .order_by(Order.created_date.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "orders/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        pending_orders=pending_orders,
        fulfilled_orders=fulfilled_orders,
    )


@order_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new medication order."""
    # Find the visit this order is for
    visit_id = request.args.get("visit_id", None, type=int)
    # Check if this is for gap coverage (when visit was postponed)
    gap_coverage = request.args.get("gap_coverage", "false").strip().lower() == "true"
    visit = None

    if visit_id:
        visit = PhysicianVisit.query.get_or_404(visit_id)
    else:
        # If no visit specified, use the next upcoming visit
        visit = (
            PhysicianVisit.query.filter(
                PhysicianVisit.visit_date >= datetime.now(timezone.utc)
            )
            .order_by(PhysicianVisit.visit_date)
            .first()
        )

    if not visit:
        flash(
            _("No upcoming physician visit found. Please schedule a visit first."),
            "warning",
        )
        return redirect(url_for("visits.new"))

    if request.method == "POST":
        # Create new order
        order = Order(physician_visit_id=visit.id, status="planned")
        db.session.add(order)

        # Filter medications based on the visit's physician
        if visit.physician_id:
            # If visit has a physician, only show prescription medications assigned to that physician (no OTC)
            medications = Medication.query.filter(
                (Medication.physician_id == visit.physician_id) & (Medication.is_otc.is_(False))
            ).all()
        else:
            # If visit has no physician, show no medications (can't create prescription orders without physician)
            medications = []

        # Process each medication
        for med in medications:
            if f"include_{med.id}" in request.form:
                # Extract form data
                quantity_needed = int(request.form.get(f"quantity_{med.id}", 0) or 0)
                packages_n1 = int(request.form.get(f"packages_n1_{med.id}", 0) or 0)
                packages_n2 = int(request.form.get(f"packages_n2_{med.id}", 0) or 0)
                packages_n3 = int(request.form.get(f"packages_n3_{med.id}", 0) or 0)

                # Create order item
                order_item = OrderItem(
                    medication_id=med.id,
                    quantity_needed=quantity_needed,
                    packages_n1=packages_n1,
                    packages_n2=packages_n2,
                    packages_n3=packages_n3,
                )

                order.order_items.append(order_item)

        db.session.commit()

        flash(_("Order created successfully"), "success")
        return redirect(url_for("orders.show", id=order.id))

    # Get settings to check if next-but-one is enabled globally
    from physician_visit_utils import Settings

    settings = Settings.get_settings()

    # Determine if we should calculate for next-but-one visit
    consider_next_but_one = (
        visit.order_for_next_but_one or settings.default_order_for_next_but_one
    )

    # Filter medications based on the visit's physician
    if visit.physician_id:
        # If visit has a physician, only show prescription medications assigned to that physician (no OTC)
        medications = Medication.query.filter(
            (Medication.physician_id == visit.physician_id) & (Medication.is_otc.is_(False))
        ).all()
    else:
        # If visit has no physician, show no medications (can't create prescription orders without physician)
        medications = []

    def calculate_medication_needs(med, visit_date, gap_coverage=False, consider_next_but_one=False):
        """Helper function to calculate medication needs for both gap coverage and normal orders."""
        if not med.inventory:
            return None

        if gap_coverage:
            if med.daily_usage <= 0:
                return None

            depletion_date = med.depletion_date
            if not depletion_date:
                return None

            # Ensure both dates are timezone-aware for comparison
            from utils import ensure_timezone_utc
            depletion_date = ensure_timezone_utc(depletion_date)
            visit_date = ensure_timezone_utc(visit_date)

            if depletion_date >= visit_date:
                return None

            # Calculate how much is needed from depletion date to visit date
            gap_period_units = med.calculate_needed_for_period(
                depletion_date,
                visit_date,
                include_safety_margin=True
            )

            if gap_period_units <= 0:
                return None

            # For gap coverage, the additional needed is the full gap period amount
            # because we need to order enough to bridge the gap from depletion to visit
            current = med.total_inventory_count
            additional = gap_period_units  # Always order the full gap amount
            packages = med.calculate_packages_needed(additional)
            
            logger.info(f"Gap coverage calculation for {med.name}: depletion_date={depletion_date}, visit_date={visit_date}, gap_period_units={gap_period_units}, current={current}, additional={additional}")
            
            # Calculate days until depletion for tooltip explanation
            from models.base import utcnow
            from utils import ensure_timezone_utc
            depletion_date_utc = ensure_timezone_utc(depletion_date)
            visit_date_utc = ensure_timezone_utc(visit_date)
            days_until_depletion = (depletion_date_utc - utcnow()).days
            
            return {
                "medication": med,
                "needed_units": gap_period_units,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages,
                "calculation_type": "gap_coverage",
                "depletion_date": depletion_date,
                "gap_days": (visit_date_utc - depletion_date_utc).days,
                "days_until_depletion": days_until_depletion,
                "safety_margin_days": med.safety_margin_days,
            }
        else:
            # Normal order calculation
            needed = med.calculate_needed_until_visit(
                visit_date,
                include_safety_margin=True,
                consider_next_but_one=consider_next_but_one,
            )
            current = med.total_inventory_count
            additional = max(0, needed - current)
            packages = med.calculate_packages_needed(additional)

            # Calculate breakdown for tooltip
            from models.base import utcnow
            from utils import ensure_timezone_utc
            visit_date_utc = ensure_timezone_utc(visit_date)
            days_until_visit = (visit_date_utc - utcnow()).days
            if consider_next_but_one:
                from models import Settings
                settings = Settings.get_settings()
                total_days = days_until_visit + settings.default_visit_interval
                calculation_type = "next_but_one"
            else:
                total_days = days_until_visit
                calculation_type = "standard"

            return {
                "medication": med,
                "needed_units": needed,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages,
                "calculation_type": calculation_type,
                "days_calculated": total_days,
                "base_days": days_until_visit,
                "safety_margin_days": med.safety_margin_days,
            }

    medication_needs = {}

    # Calculate needs for all medications using the helper function
    for med in medications:
        needs = calculate_medication_needs(
            med,
            visit.visit_date,
            gap_coverage=gap_coverage,
            consider_next_but_one=consider_next_but_one
        )
        if needs:
            medication_needs[med.id] = needs

    return render_template(
        "orders/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        medications=medications,
        medication_needs=medication_needs,
        consider_next_but_one=consider_next_but_one,
        gap_coverage=gap_coverage,
    )


@order_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific order."""
    order = Order.query.get_or_404(id)

    return render_template(
        "orders/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        order=order,
        visit=order.physician_visit,
        order_items=order.order_items,
    )


@order_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing order."""
    order = Order.query.get_or_404(id)

    # Don't allow editing fulfilled orders
    if order.status == "fulfilled":
        flash(_("Cannot edit fulfilled orders"), "error")
        return redirect(url_for("orders.show", id=order.id))

    if request.method == "POST":
        # Update order status if provided
        new_status = request.form.get("status")
        if new_status in ["planned", "partial", "fulfilled"]:
            order.status = new_status

        # Filter medications based on the visit's physician
        visit = order.physician_visit
        if visit.physician_id:
            # If visit has a physician, only show prescription medications assigned to that physician (no OTC)
            medications = Medication.query.filter(
                (Medication.physician_id == visit.physician_id) & (Medication.is_otc.is_(False))
            ).all()
        else:
            # If visit has no physician, show no medications (can't create prescription orders without physician)
            medications = []

        # Track which medications are included in the updated order
        included_med_ids = set()

        # Process each medication
        for med in medications:
            if f"include_{med.id}" in request.form:
                included_med_ids.add(med.id)

                # Extract form data
                quantity_needed = int(request.form.get(f"quantity_{med.id}", 0) or 0)
                packages_n1 = int(request.form.get(f"packages_n1_{med.id}", 0) or 0)
                packages_n2 = int(request.form.get(f"packages_n2_{med.id}", 0) or 0)
                packages_n3 = int(request.form.get(f"packages_n3_{med.id}", 0) or 0)

                # Find existing order item or create new one
                order_item = None
                for item in order.order_items:
                    if item.medication_id == med.id:
                        order_item = item
                        break

                if order_item is None:
                    order_item = OrderItem(order_id=order.id, medication_id=med.id)
                    db.session.add(order_item)
                    order.order_items.append(order_item)

                # Update order item
                order_item.quantity_needed = quantity_needed
                order_item.packages_n1 = packages_n1
                order_item.packages_n2 = packages_n2
                order_item.packages_n3 = packages_n3

        # Remove items that are no longer included
        for item in list(order.order_items):
            if item.medication_id not in included_med_ids:
                db.session.delete(item)
                order.order_items.remove(item)

        db.session.commit()

        flash(_("Order updated successfully"), "success")
        return redirect(url_for("orders.show", id=order.id))

    # Filter medications based on the visit's physician
    visit = order.physician_visit
    if visit.physician_id:
        # If visit has a physician, only show prescription medications assigned to that physician (no OTC)
        medications = Medication.query.filter(
            (Medication.physician_id == visit.physician_id) & (Medication.is_otc.is_(False))
        ).all()
    else:
        # If visit has no physician, show no medications (can't create prescription orders without physician)
        medications = []

    # Create a lookup map for existing order items
    order_items_map = {item.medication_id: item for item in order.order_items}

    return render_template(
        "orders/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        order=order,
        visit=order.physician_visit,
        medications=medications,
        order_items_map=order_items_map,
    )


@order_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete an order."""
    order = Order.query.get_or_404(id)

    # Don't allow deleting fulfilled orders
    if order.status == "fulfilled":
        flash(_("Cannot delete fulfilled orders"), "error")
        return redirect(url_for("orders.show", id=order.id))

    # Delete all associated order items
    for item in order.order_items:
        db.session.delete(item)

    db.session.delete(order)
    db.session.commit()

    flash(_("Order deleted successfully"), "success")
    return redirect(url_for("orders.index"))


@order_bp.route("/<int:id>/printable")
def printable(id: int):
    """Generate a printable view of the order."""
    order = Order.query.get_or_404(id)

    # No need to update status when generating printable view
    # The status is managed through the regular workflow

    # Render a printer-friendly template
    response = make_response(
        render_template(
            "orders/printable.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            order=order,
            visit=order.physician_visit,
            order_items=order.order_items,
            print_date=datetime.now(timezone.utc),
        )
    )

    # Set headers to hint this is for printing
    response.headers["Content-Disposition"] = f"inline; filename=order_{order.id}.html"

    return response


@order_bp.route("/<int:id>/update_status", methods=["POST"])
def update_status(id: int):
    """Update order status from dropdown."""
    order = Order.query.get_or_404(id)
    
    new_status = request.form.get("status")
    if new_status in ["planned", "partial", "fulfilled"]:
        old_status = order.status
        order.status = new_status
        
        # If manually setting to fulfilled, mark all pending items as fulfilled
        if new_status == "fulfilled" and old_status != "fulfilled":
            for item in order.order_items:
                if item.fulfillment_status == "pending":
                    item.fulfillment_status = "fulfilled"
                    item.fulfilled_at = datetime.now(timezone.utc)
                    item.fulfilled_quantity = item.total_units_ordered
        
        # If manually setting from fulfilled/partial to planned, reset fulfilled items
        elif old_status in ["fulfilled", "partial"] and new_status == "planned":
            for item in order.order_items:
                if item.fulfillment_status in ["fulfilled", "modified"]:
                    item.fulfillment_status = "pending"
                    item.fulfilled_at = None
                    item.fulfilled_quantity = None
        
        # Note: We don't change item status when manually setting to "partial"
        # as this should reflect the actual state of individual items
        
        db.session.commit()
        flash(_("Order status updated to {}").format(new_status.capitalize()), "success")
    else:
        flash(_("Invalid status"), "error")
    
    return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:id>/toggle_fulfillment", methods=["POST"])
def toggle_fulfillment(id: int):
    """Toggle order fulfillment status with optional inventory update."""
    order = Order.query.get_or_404(id)
    
    if order.status == "fulfilled":
        # Unfulfill the order
        order.status = "planned"
        # Mark all items as pending
        for item in order.order_items:
            item.fulfillment_status = "pending"
            item.fulfilled_at = None
        flash(_("Order marked as unfulfilled"), "info")
    else:
        # Get fulfillment type from form
        fulfillment_type = request.form.get("fulfillment_type", "mark_only")
        update_inventory = fulfillment_type == "update_inventory"
        
        # Mark as fulfilled
        order.status = "fulfilled"
        fulfilled_count = 0
        
        # Mark all pending items as fulfilled
        for item in order.order_items:
            if item.fulfillment_status != "fulfilled":
                item.fulfillment_status = "fulfilled"
                item.fulfilled_at = datetime.now(timezone.utc)
                item.fulfilled_quantity = item.total_units_ordered
                fulfilled_count += 1
                
                # Update inventory if requested
                if update_inventory and item.medication and item.medication.inventory:
                    item.medication.inventory.update_count(
                        item.total_units_ordered,
                        f"Bulk fulfillment from order #{order.id}"
                    )
        
        if update_inventory:
            flash(_("Order marked as fulfilled and {} items added to inventory").format(fulfilled_count), "success")
        else:
            flash(_("Order marked as fulfilled"), "success")
    
    db.session.commit()
    
    # Check if there's a specific redirect requested or use referrer
    redirect_to = request.form.get("redirect_to")
    if redirect_to == "index":
        return redirect(url_for("orders.index"))
    elif request.referrer and "/orders/" in request.referrer and request.referrer.endswith("/orders/"):
        # Came from orders index page
        return redirect(url_for("orders.index"))
    else:
        # Default to showing the order details
        return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:id>/item/<int:item_id>/fulfill", methods=["POST"])
def fulfill_item(id: int, item_id: int):
    """Mark individual order item as fulfilled and optionally update inventory."""
    order = Order.query.get_or_404(id)
    item = OrderItem.query.get_or_404(item_id)
    
    if item.order_id != order.id:
        flash(_("Item does not belong to this order"), "error")
        return redirect(url_for("orders.show", id=order.id))
    
    # Get form data
    status = request.form.get("status", "fulfilled")
    notes = request.form.get("notes", "")
    add_to_inventory = request.form.get("add_to_inventory") == "true"
    custom_quantity = request.form.get("custom_quantity", type=int)
    
    # Update item status
    item.fulfillment_status = status
    item.fulfillment_notes = notes if notes else None
    item.fulfilled_at = datetime.now(timezone.utc) if status == "fulfilled" else None
    
    # Handle quantity and inventory update
    if status == "fulfilled" and add_to_inventory and item.medication and item.medication.inventory:
        # Use custom quantity or calculate from packages
        if custom_quantity is not None:
            total_units = custom_quantity
            item.fulfilled_quantity = custom_quantity
        else:
            total_units = item.total_units_ordered
            item.fulfilled_quantity = total_units
        
        # Update inventory
        item.medication.inventory.update_count(
            total_units, 
            f"Added from order #{order.id} - {notes if notes else 'Standard fulfillment'}"
        )
    elif status == "modified" and custom_quantity is not None:
        item.fulfilled_quantity = custom_quantity
        if add_to_inventory and item.medication and item.medication.inventory:
            item.medication.inventory.update_count(
                custom_quantity,
                f"Modified fulfillment from order #{order.id} - {notes if notes else 'Modified quantity'}"
            )
    
    # Update order status based on all items
    order.update_status_from_items()
    db.session.commit()
    
    flash(_("Item {} marked as {}").format(item.medication.name if item.medication else _("Unknown"), status), "success")
    return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:id>/bulk_fulfill", methods=["POST"])
def bulk_fulfill(id: int):
    """Process bulk fulfillment of multiple items."""
    order = Order.query.get_or_404(id)
    
    # Get selected items from form
    selected_items = request.form.getlist("items")
    add_to_inventory = request.form.get("add_to_inventory") == "true"
    
    fulfilled_count = 0
    for item_id in selected_items:
        item = OrderItem.query.get(item_id)
        if item and item.order_id == order.id and item.fulfillment_status != "fulfilled":
            item.fulfillment_status = "fulfilled"
            item.fulfilled_at = datetime.now(timezone.utc)
            item.fulfilled_quantity = item.total_units_ordered
            
            if add_to_inventory and item.medication and item.medication.inventory:
                item.medication.inventory.update_count(
                    item.total_units_ordered,
                    f"Bulk fulfillment from order #{order.id}"
                )
            fulfilled_count += 1
    
    # Update order status
    order.update_status_from_items()
    db.session.commit()
    
    flash(_("Successfully fulfilled {} items").format(fulfilled_count), "success")
    return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:order_id>/item/<int:item_id>/cancel", methods=["POST"])
def cancel_item(order_id: int, item_id: int):
    """Cancel an individual order item."""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.get_or_404(item_id)
    
    # Verify item belongs to order
    if item.order_id != order.id:
        flash(_("Invalid order item"), "error")
        return redirect(url_for("orders.show", id=order_id))
    
    # Only allow canceling pending items
    if item.fulfillment_status != "pending":
        flash(_("Can only cancel pending items"), "warning")
        return redirect(url_for("orders.show", id=order_id))
    
    # Cancel the item
    item.fulfillment_status = "cancelled"
    
    # Update order status
    order.update_status_from_items()
    db.session.commit()
    
    flash(_("Item cancelled successfully"), "success")
    return redirect(url_for("orders.show", id=order_id))


@order_bp.route("/<int:order_id>/item/<int:item_id>/undo_cancel", methods=["POST"])
def undo_cancel_item(order_id: int, item_id: int):
    """Undo cancellation of an order item."""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.get_or_404(item_id)
    
    # Verify item belongs to order
    if item.order_id != order.id:
        flash(_("Invalid order item"), "error")
        return redirect(url_for("orders.show", id=order_id))
    
    # Only allow undoing cancellation for cancelled items
    if item.fulfillment_status != "cancelled":
        flash(_("Can only undo cancellation for cancelled items"), "warning")
        return redirect(url_for("orders.show", id=order_id))
    
    # Restore the item to pending status
    item.fulfillment_status = "pending"
    item.fulfillment_notes = None  # Clear any cancellation notes
    item.fulfilled_quantity = None
    item.fulfilled_at = None
    
    # Update order status
    order.update_status_from_items()
    db.session.commit()
    
    flash(_("Cancellation undone successfully"), "success")
    return redirect(url_for("orders.show", id=order_id))


@order_bp.route("/<int:id>/prescription", methods=["GET"])
def prescription(id: int):
    """Generate a prescription PDF for the order."""
    order = Order.query.get_or_404(id)

    # Check if there's an active prescription template
    from models import PrescriptionTemplate

    active_template = PrescriptionTemplate.get_active_template()

    if not active_template:
        flash(
            _("No active prescription template found. Please configure a template first."),
            "warning",
        )
        return redirect(url_for("prescriptions.index"))

    # Generate the PDF
    pdf_path = generate_prescription_pdf(order.id)

    if pdf_path:
        # Determine the filename for download
        filename = f"prescription_order_{order.id}.pdf"

        # Return the file for download
        return send_file(pdf_path, download_name=filename, as_attachment=True)
    else:
        flash(_("Error generating prescription PDF"), "error")
        return redirect(url_for("orders.show", id=id))


@order_bp.route("/item/<int:item_id>/search_packages")
def search_packages(item_id: int):
    """Search for packages by serial number for linking to an order item."""
    from models import PackageInventory
    
    order_item = OrderItem.query.get_or_404(item_id)
    search_term = request.args.get('search', '').strip()
    
    if not search_term:
        return {"packages": []}
    
    # Get the order date
    order_date = order_item.order.created_date
    
    # Search for packages by serial number that:
    # 1. Belong to the same medication
    # 2. Are not yet linked to any order
    # 3. Were scanned after the order was created
    # 4. Match the search term
    from models import ScannedItem
    
    available = PackageInventory.query.join(PackageInventory.scanned_item).filter(
        PackageInventory.medication_id == order_item.medication_id,
        PackageInventory.order_item_id.is_(None),
        PackageInventory.status.in_(["sealed", "open"]),
        ScannedItem.scanned_at >= order_date,
        ScannedItem.serial_number.ilike(f"%{search_term}%")
    ).limit(10).all()
    
    # Format for JSON response
    packages_data = []
    for pkg in available:
        packages_data.append({
            "id": pkg.id,
            "serial_number": pkg.scanned_item.serial_number if pkg.scanned_item else "No S/N",
            "status": pkg.status,
            "units": pkg.current_units,
            "scanned_date": pkg.scanned_item.scanned_at.strftime("%Y-%m-%d") if pkg.scanned_item and pkg.scanned_item.scanned_at else ""
        })
    
    return {"packages": packages_data}


@order_bp.route("/item/<int:item_id>/link_package/<int:package_id>", methods=["POST"])
def link_package(item_id: int, package_id: int):
    """Link a package to an order item."""
    from models import PackageInventory
    
    order_item = OrderItem.query.get_or_404(item_id)
    package = PackageInventory.query.get_or_404(package_id)
    
    # Verify the package belongs to the same medication
    if package.medication_id != order_item.medication_id:
        flash(_("Package does not belong to this medication"), "error")
        return redirect(url_for("orders.show", id=order_item.order_id))
    
    # Link the package to the order item
    package.order_item_id = order_item.id
    
    # Flush to ensure the relationship is visible
    db.session.flush()
    
    # Update order status if needed
    order = order_item.order
    # Always check status when linking packages (don't restrict to certain statuses)
    if order.status != "fulfilled":
        # Count total packages needed and linked
        total_needed = 0
        total_linked = 0
        for item in order.order_items:
            total_needed += item.packages_n1 + item.packages_n2 + item.packages_n3
            # Refresh the item to get updated linked_packages
            db.session.refresh(item)
            total_linked += len(item.linked_packages) if item.linked_packages else 0
        
        print(f"DEBUG: Order {order.id} - Current status: {order.status}, Linked: {total_linked}, Needed: {total_needed}")
        
        if total_linked == 0:
            # Keep current status if no packages linked
            if order.status == "partial":
                order.status = "planned"
        elif total_linked < total_needed and total_linked > 0:
            print(f"DEBUG: Setting order {order.id} to partial")
            order.status = "partial"
        elif total_linked == total_needed and total_needed > 0:
            # All packages are linked - mark as fulfilled
            print(f"DEBUG: Setting order {order.id} to fulfilled")
            order.status = "fulfilled"
            # Also update item fulfillment status
            for item in order.order_items:
                if item.fulfillment_status == "pending":
                    item.fulfillment_status = "fulfilled"
                    item.fulfilled_quantity = item.total_units_ordered
                    item.fulfilled_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(_("Package linked successfully"), "success")
    return redirect(url_for("orders.show", id=order_item.order_id))


@order_bp.route("/item/<int:item_id>/unlink_package/<int:package_id>", methods=["POST"])
def unlink_package(item_id: int, package_id: int):
    """Unlink a package from an order item."""
    from models import PackageInventory
    
    order_item = OrderItem.query.get_or_404(item_id)
    package = PackageInventory.query.get_or_404(package_id)
    
    # Verify the package is linked to this order item
    if package.order_item_id != order_item.id:
        flash(_("Package is not linked to this order item"), "error")
        return redirect(url_for("orders.show", id=order_item.order_id))
    
    # Unlink the package from the order item
    package.order_item_id = None
    
    # Update order status if needed
    order = order_item.order
    if order.status in ["partial", "fulfilled"]:
        # Ensure the unlink is visible in the query
        db.session.flush()
        
        # Count total packages needed and linked
        total_needed = 0
        total_linked = 0
        for item in order.order_items:
            total_needed += item.packages_n1 + item.packages_n2 + item.packages_n3
            total_linked += len(item.linked_packages) if item.linked_packages else 0
        
        if total_linked == 0:
            order.status = "planned"
            # Reset fulfillment status if it was fulfilled
            for item in order.order_items:
                if item.fulfillment_status == "fulfilled":
                    item.fulfillment_status = "pending"
                    item.fulfilled_quantity = None
                    item.fulfilled_at = None
        elif total_linked < total_needed:
            order.status = "partial"
            # Reset fulfillment status if it was fulfilled
            for item in order.order_items:
                if item.fulfillment_status == "fulfilled":
                    item.fulfillment_status = "pending"
                    item.fulfilled_quantity = None
                    item.fulfilled_at = None
    
    db.session.commit()
    
    flash(_("Package unlinked successfully"), "success")
    return redirect(url_for("orders.show", id=order_item.order_id))
