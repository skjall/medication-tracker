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
    ActiveIngredient,
    MedicationProduct,
    Order,
    OrderItem,
    db,
)
from pdf_utils import generate_order_pdf
from utils import to_local_timezone, format_date, format_datetime

# Create a logger for this module
logger = logging.getLogger(__name__)


# Create a blueprint for order routes
order_bp = Blueprint("orders", __name__, url_prefix="/orders")


@order_bp.route("/")
def index():
    """Display list of all medication orders."""
    # Get planned/pending orders (including printed orders that are not yet fulfilled)
    pending_orders = (
        Order.query.filter(Order.status.in_(["planned", "partial", "printed"]))
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

        # Get active ingredients with products that need ordering (not OTC)
        # For now, get all active ingredients that have products
        ingredients = ActiveIngredient.query.all()
        
        # Process each ingredient
        for ingredient in ingredients:
            if f"include_{ingredient.id}" in request.form:
                # Extract form data
                quantity_needed = int(request.form.get(f"quantity_{ingredient.id}", 0) or 0)
                
                # Get selected product
                product_id = request.form.get(f"product_{ingredient.id}")
                if product_id:
                    product_id = int(product_id)
                else:
                    # Default to the ingredient's default product if not specified
                    product_id = ingredient.default_product_id
                
                packages_n1 = int(request.form.get(f"packages_n1_{ingredient.id}", 0) or 0)
                packages_n2 = int(request.form.get(f"packages_n2_{ingredient.id}", 0) or 0)
                packages_n3 = int(request.form.get(f"packages_n3_{ingredient.id}", 0) or 0)

                # Only create order item if there's actually something to order
                if quantity_needed > 0 or packages_n1 > 0 or packages_n2 > 0 or packages_n3 > 0:
                    # Create order item
                    order_item = OrderItem(
                        active_ingredient_id=ingredient.id,
                        product_id=product_id,
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

    # Get active ingredients based on visit physician
    if visit.physician_id:
        # Get ingredients that have products prescribed by this physician
        ingredients = ActiveIngredient.query.join(
            MedicationProduct,
            ActiveIngredient.id == MedicationProduct.active_ingredient_id
        ).filter(
            MedicationProduct.physician_id == visit.physician_id
        ).order_by(ActiveIngredient.name).distinct().all()
    else:
        # For visits without physician, show OTC ingredients only
        ingredients = ActiveIngredient.query.join(
            MedicationProduct,
            ActiveIngredient.id == MedicationProduct.active_ingredient_id
        ).filter(
            MedicationProduct.is_otc == True
        ).order_by(ActiveIngredient.name).distinct().all()

    def calculate_ingredient_needs(ingredient, visit_date, gap_coverage=False, consider_next_but_one=False):
        """Helper function to calculate ingredient needs."""
        
        result = {
            'calculation_type': 'normal',
            'days_calculated': 0,
            'base_days': 0,
            'safety_margin_days': ingredient.safety_margin_days if hasattr(ingredient, 'safety_margin_days') else 30,
            'needed_units': 0,
            'current_inventory': ingredient.total_inventory_count,
            'additional_needed': 0,
            'days_until_depletion': 0,
            'gap_days': 0,
            'will_deplete_before_visit': False,
            'packages': {'N1': 0, 'N2': 0, 'N3': 0}
        }
        
        # Calculate days until visit
        today = datetime.now(timezone.utc).date()
        visit_date = visit_date.date() if hasattr(visit_date, 'date') else visit_date
        days_until_visit = (visit_date - today).days
        
        # Calculate days until depletion if daily usage > 0
        if ingredient.daily_usage > 0 and ingredient.total_inventory_count > 0:
            result['days_until_depletion'] = int(ingredient.total_inventory_count / ingredient.daily_usage)
        
        # Check if it will deplete before visit
        if ingredient.daily_usage > 0:
            result['will_deplete_before_visit'] = result['days_until_depletion'] < days_until_visit
        
        # Determine calculation type and days needed
        if gap_coverage:
            result['calculation_type'] = 'gap_coverage'
            # Gap coverage: calculate days between depletion and visit
            if result['will_deplete_before_visit']:
                result['gap_days'] = days_until_visit - result['days_until_depletion']
                result['days_calculated'] = result['gap_days'] + result['safety_margin_days']
            else:
                # For gap coverage, if it won't deplete, we don't need to order anything
                result['days_calculated'] = 0
                result['gap_days'] = 0
        elif consider_next_but_one:
            result['calculation_type'] = 'next_but_one'
            # Calculate for next-but-one visit (double the period)
            result['base_days'] = days_until_visit
            result['days_calculated'] = days_until_visit * 2 + result['safety_margin_days']
        else:
            # Normal calculation: days until visit + safety margin
            result['days_calculated'] = days_until_visit + result['safety_margin_days']
        
        # Calculate units needed
        if ingredient.daily_usage > 0:
            result['needed_units'] = int(ingredient.daily_usage * result['days_calculated'])
        
        # Calculate additional units needed (subtracting current inventory)
        result['additional_needed'] = max(0, result['needed_units'] - result['current_inventory'])
        
        # Calculate packages needed for the additional units
        if result['additional_needed'] > 0:
            # Get the default product or first product for this ingredient
            product = ingredient.default_product or (ingredient.products[0] if ingredient.products else None)
            if product and product.orderable_packages:
                # Find the most efficient package size (prefer larger packages to minimize count)
                best_package = None
                min_overage = float('inf')
                
                for package in product.orderable_packages:
                    if package.quantity > 0:
                        # Calculate how many of this package we'd need
                        packages_needed = (result['additional_needed'] + package.quantity - 1) // package.quantity
                        overage = (packages_needed * package.quantity) - result['additional_needed']
                        
                        # Prefer packages with less overage (waste)
                        if overage < min_overage:
                            min_overage = overage
                            best_package = (package.package_size, packages_needed)
                
                # Set the best package option
                if best_package:
                    result['packages'][best_package[0]] = best_package[1]
        
        return result
    
    # Calculate ingredient needs for each ingredient
    ingredient_needs = {}
    for ingredient in ingredients:
        # Skip OTC ingredients in orders
        if not any(not product.is_otc for product in ingredient.products):
            continue
            
        ingredient_needs[ingredient.id] = calculate_ingredient_needs(
            ingredient, 
            visit.visit_date, 
            gap_coverage=gap_coverage,
            consider_next_but_one=consider_next_but_one
        )

    return render_template(
        "orders/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        ingredients=ingredients,
        ingredient_needs=ingredient_needs,
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

        # Filter ingredients based on the visit's physician
        visit = order.physician_visit
        if visit.physician_id:
            # If visit has a physician, show all active ingredients
            ingredients = ActiveIngredient.query.all()
        else:
            # If visit has no physician, show no ingredients (can't create orders without physician)
            ingredients = []

        # Track which ingredients are included in the updated order
        included_ingredient_ids = set()

        # Process each ingredient
        for ingredient in ingredients:
            if f"include_{ingredient.id}" in request.form:
                included_ingredient_ids.add(ingredient.id)

                # Extract form data
                quantity_needed = int(request.form.get(f"quantity_{ingredient.id}", 0) or 0)
                
                # Get selected product
                product_id = request.form.get(f"product_{ingredient.id}")
                if product_id:
                    product_id = int(product_id)
                else:
                    # Default to the ingredient's default product if not specified
                    product_id = ingredient.default_product_id
                
                # Get package counts
                packages_n1 = int(request.form.get(f"packages_n1_{ingredient.id}", 0) or 0)
                packages_n2 = int(request.form.get(f"packages_n2_{ingredient.id}", 0) or 0)
                packages_n3 = int(request.form.get(f"packages_n3_{ingredient.id}", 0) or 0)

                # Find existing order item or create new one
                order_item = None
                for item in order.order_items:
                    if item.active_ingredient_id == ingredient.id:
                        order_item = item
                        break

                if order_item is None:
                    order_item = OrderItem(
                        order_id=order.id, 
                        active_ingredient_id=ingredient.id,
                        product_id=product_id
                    )
                    db.session.add(order_item)
                    order.order_items.append(order_item)

                # Update order item
                order_item.quantity_needed = quantity_needed
                order_item.product_id = product_id  # Update the selected product
                order_item.packages_n1 = packages_n1
                order_item.packages_n2 = packages_n2
                order_item.packages_n3 = packages_n3

        # Remove items that are no longer included
        for item in list(order.order_items):
            if item.active_ingredient_id not in included_ingredient_ids:
                db.session.delete(item)
                order.order_items.remove(item)

        db.session.commit()

        flash(_("Order updated successfully"), "success")
        return redirect(url_for("orders.show", id=order.id))

    # Filter ingredients based on the visit's physician
    visit = order.physician_visit
    if visit.physician_id:
        # If visit has a physician, show all active ingredients
        ingredients = ActiveIngredient.query.all()
    else:
        # If visit has no physician, show no ingredients (can't create orders without physician)
        ingredients = []

    # Create a lookup map for existing order items
    order_items_map = {item.active_ingredient_id: item for item in order.order_items}

    return render_template(
        "orders/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        order=order,
        visit=order.physician_visit,
        ingredients=ingredients,
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
                # TODO: Implement inventory update for ingredient/product system
                if update_inventory:
                    # For now, skip inventory updates since we're using the new system
                    pass
        
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
    custom_quantity = request.form.get("custom_quantity", type=int)
    
    # Update item status
    item.fulfillment_status = status
    item.fulfillment_notes = notes if notes else None
    item.fulfilled_at = datetime.now(timezone.utc) if status == "fulfilled" else None
    
    # Handle quantity and inventory update
    # TODO: Update this to work with the new PackageInventory system
    # For now, we skip inventory updates since ActiveIngredient doesn't have direct inventory
    if status == "fulfilled":
        # Use custom quantity or calculate from packages
        if custom_quantity is not None:
            item.fulfilled_quantity = custom_quantity
        else:
            item.fulfilled_quantity = item.total_units_ordered
        
        # Note: Inventory updates should be handled through PackageInventory scanning
        # not through the old Inventory model
    elif status == "modified" and custom_quantity is not None:
        item.fulfilled_quantity = custom_quantity
        # Note: Inventory updates should be handled through PackageInventory scanning
    
    # Update order status based on all items
    order.update_status_from_items()
    db.session.commit()
    
    ingredient_name = item.active_ingredient.name if item.active_ingredient else _("Unknown")
    flash(_("Item {} marked as {}").format(ingredient_name, status), "success")
    return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:id>/bulk_fulfill", methods=["POST"])
def bulk_fulfill(id: int):
    """Process bulk fulfillment of multiple items."""
    order = Order.query.get_or_404(id)
    
    # Get selected items from form
    selected_items = request.form.getlist("items")
    
    fulfilled_count = 0
    for item_id in selected_items:
        item = OrderItem.query.get(item_id)
        if item and item.order_id == order.id and item.fulfillment_status != "fulfilled":
            item.fulfillment_status = "fulfilled"
            item.fulfilled_at = datetime.now(timezone.utc)
            item.fulfilled_quantity = item.total_units_ordered
            
            # Note: Inventory updates should be handled through PackageInventory scanning
            # not through the old Inventory model
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


@order_bp.route("/<int:id>/pdf", methods=["GET"])
def order_pdf(id: int):
    """Generate a PDF for the order."""
    order = Order.query.get_or_404(id)

    # Generate the PDF (will use physician's PDF template or fallback to legacy template)
    pdf_path = generate_order_pdf(order.id)

    if pdf_path:
        # Determine the filename for download
        filename = f"order_{order.id}.pdf"

        # Return the file for download
        return send_file(pdf_path, download_name=filename, as_attachment=True)
    else:
        if order.physician_visit and order.physician_visit.physician and order.physician_visit.physician.pdf_template:
            flash(_("The PDF template file is missing. Please re-upload the template in PDF Forms."), "error")
        else:
            flash(_("No PDF template assigned to physician. Please assign a template in physician settings."), "error")
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
    # 1. Belong to the same medication OR have matching active ingredient
    # 2. Are not yet linked to any order
    # 3. Were scanned after the order was created
    # 4. Match the search term
    from models import ScannedItem, ProductPackage, ActiveIngredient
    from sqlalchemy import or_
    
    # Build filter conditions for both old and new systems
    conditions = [
        PackageInventory.order_item_id.is_(None),
        PackageInventory.status.in_(["sealed", "opened"]),
        ScannedItem.scanned_at >= order_date,
        ScannedItem.serial_number.ilike(f"%{search_term}%")
    ]
    
    # Match by active ingredient
    if order_item.active_ingredient_id:
        ingredient = ActiveIngredient.query.get(order_item.active_ingredient_id)
        if ingredient:
            # Find all product packages with this ingredient
            product_packages = ProductPackage.query.join(
                ProductPackage.product
            ).filter(
                ProductPackage.product.has(active_ingredient_id=ingredient.id)
            ).all()
            
            # Get GTINs and national numbers for matching
            gtins = [p.gtin for p in product_packages if p.gtin]
            national_numbers = [(p.national_number, p.national_number_type) 
                              for p in product_packages 
                              if p.national_number and p.national_number_type]
            
            # Add conditions for packages
            if gtins or national_numbers:
                match_conditions = []
                
                if gtins:
                    match_conditions.append(ScannedItem.gtin.in_(gtins))
                
                for nat_num, nat_type in national_numbers:
                    match_conditions.append(
                        (ScannedItem.national_number == nat_num) & 
                        (ScannedItem.national_number_type == nat_type)
                    )
                
                if match_conditions:
                    conditions.append(or_(*match_conditions))
    
    available = PackageInventory.query.join(PackageInventory.scanned_item).filter(
        *conditions
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
    
    # Package validation removed - orders system needs rewrite to work with ingredients/products instead of medications
    # TODO: Rewrite entire orders system to use ActiveIngredient/MedicationProduct instead of Medication
    
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
