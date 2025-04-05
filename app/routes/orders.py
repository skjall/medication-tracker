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
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

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
        Order.query.filter(Order.status.in_(["planned", "printed"]))
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
            "No upcoming physician visit found. Please schedule a visit first.",
            "warning",
        )
        return redirect(url_for("visits.new"))

    if request.method == "POST":
        # Create new order
        order = Order(hospital_visit_id=visit.id, status="planned")
        db.session.add(order)

        # Get all medications
        medications = Medication.query.all()

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

        flash("Order created successfully", "success")
        return redirect(url_for("orders.show", id=order.id))

    # Get settings to check if next-but-one is enabled globally
    from physician_visit_utils import Settings

    settings = Settings.get_settings()

    # Determine if we should calculate for next-but-one visit
    consider_next_but_one = (
        visit.order_for_next_but_one or settings.default_order_for_next_but_one
    )

    # Calculate medication needs for the visit
    medications = Medication.query.all()
    medication_needs = {}

    for med in medications:
        if med.inventory:
            # Use the enhanced calculation that considers next-but-one setting
            needed = med.calculate_needed_until_visit(
                visit.visit_date,
                include_safety_margin=True,
                consider_next_but_one=consider_next_but_one,
            )
            current = med.inventory.current_count
            additional = max(0, needed - current)
            packages = med.calculate_packages_needed(additional)

            medication_needs[med.id] = {
                "medication": med,
                "needed_units": needed,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages,
            }

    return render_template(
        "orders/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        medications=medications,
        medication_needs=medication_needs,
        consider_next_but_one=consider_next_but_one,
    )


@order_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific order."""
    order = Order.query.get_or_404(id)

    return render_template(
        "orders/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        order=order,
        visit=order.hospital_visit,
        order_items=order.order_items,
    )


@order_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing order."""
    order = Order.query.get_or_404(id)

    # Don't allow editing fulfilled orders
    if order.status == "fulfilled":
        flash("Cannot edit fulfilled orders", "error")
        return redirect(url_for("orders.show", id=order.id))

    if request.method == "POST":
        # Update order status if provided
        new_status = request.form.get("status")
        if new_status in ["planned", "printed", "fulfilled"]:
            order.status = new_status

        # Get all medications
        medications = Medication.query.all()

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

        flash("Order updated successfully", "success")
        return redirect(url_for("orders.show", id=order.id))

    # Get all medications for the form
    medications = Medication.query.all()

    # Create a lookup map for existing order items
    order_items_map = {item.medication_id: item for item in order.order_items}

    return render_template(
        "orders/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        order=order,
        visit=order.hospital_visit,
        medications=medications,
        order_items_map=order_items_map,
    )


@order_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete an order."""
    order = Order.query.get_or_404(id)

    # Don't allow deleting fulfilled orders
    if order.status == "fulfilled":
        flash("Cannot delete fulfilled orders", "error")
        return redirect(url_for("orders.show", id=order.id))

    # Delete all associated order items
    for item in order.order_items:
        db.session.delete(item)

    db.session.delete(order)
    db.session.commit()

    flash("Order deleted successfully", "success")
    return redirect(url_for("orders.index"))


@order_bp.route("/<int:id>/printable")
def printable(id: int):
    """Generate a printable view of the order."""
    order = Order.query.get_or_404(id)

    # Mark as printed if not already
    if order.status == "planned":
        order.status = "printed"
        db.session.commit()

    # Render a printer-friendly template
    response = make_response(
        render_template(
            "orders/printable.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            order=order,
            visit=order.hospital_visit,
            order_items=order.order_items,
            print_date=datetime.now(timezone.utc),
        )
    )

    # Set headers to hint this is for printing
    response.headers["Content-Disposition"] = f"inline; filename=order_{order.id}.html"

    return response


@order_bp.route("/<int:id>/fulfill", methods=["POST"])
def fulfill(id: int):
    """Mark an order as fulfilled and update inventory."""
    order = Order.query.get_or_404(id)

    # Don't allow fulfilling already fulfilled orders
    if order.status == "fulfilled":
        flash("Order is already fulfilled", "warning")
        return redirect(url_for("orders.show", id=order.id))

    # Update inventory based on the order
    for item in order.order_items:
        if item.medication and item.medication.inventory:
            # Calculate total pills from packages
            total_units = 0
            if item.medication.package_size_n1:
                total_units += item.packages_n1 * item.medication.package_size_n1
            if item.medication.package_size_n2:
                total_units += item.packages_n2 * item.medication.package_size_n2
            if item.medication.package_size_n3:
                total_units += item.packages_n3 * item.medication.package_size_n3

            # Update inventory
            item.medication.inventory.update_count(
                total_units, f"Added from order #{order.id}"
            )

    # Mark order as fulfilled
    order.status = "fulfilled"
    db.session.commit()

    flash("Order fulfilled and inventory updated successfully", "success")
    return redirect(url_for("orders.show", id=order.id))


@order_bp.route("/<int:id>/prescription", methods=["GET"])
def prescription(id: int):
    """Generate a prescription PDF for the order."""
    order = Order.query.get_or_404(id)

    # Check if there's an active prescription template
    from models import PrescriptionTemplate

    active_template = PrescriptionTemplate.get_active_template()

    if not active_template:
        flash(
            "No active prescription template found. Please configure a template first.",
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
        flash("Error generating prescription PDF", "error")
        return redirect(url_for("orders.show", id=id))
