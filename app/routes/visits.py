"""
Routes for hospital visit management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import Blueprint, flash, redirect, render_template, request, url_for

# Local application imports
from models import HospitalVisit, Medication, Order, db, utcnow
from utils import to_local_timezone

# Get a logger specific to this module
logger = logging.getLogger(__name__)

# Create a blueprint for visit routes
visit_bp = Blueprint("visits", __name__, url_prefix="/visits")


@visit_bp.route("/")
def index():
    """Display list of all hospital visits."""
    # Log at various levels to demonstrate the system
    logger.debug("Accessing visits index page")
    logger.info(f"Current time (UTC): {utcnow()}")

    # Get upcoming visits - now using utcnow() from models
    upcoming_visits = (
        HospitalVisit.query.filter(HospitalVisit.visit_date >= utcnow())
        .order_by(HospitalVisit.visit_date)
        .all()
    )

    logger.info(f"Found {len(upcoming_visits)} upcoming visits")
    logger.debug(f"Upcoming visits: {[visit.id for visit in upcoming_visits]}")

    # Get past visits
    past_visits = (
        HospitalVisit.query.filter(HospitalVisit.visit_date < utcnow())
        .order_by(HospitalVisit.visit_date.desc())
        .limit(10)
        .all()
    )

    logger.info(f"Found {len(past_visits)} past visits (limited to 10)")
    logger.debug(f"Past visits: {[visit.id for visit in past_visits]}")

    return render_template(
        "visits/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        upcoming_visits=upcoming_visits,
        past_visits=past_visits,
    )


@visit_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new hospital visit."""
    logger.debug("Accessing new visit page")

    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        logger.debug(f"New visit form data: date={visit_date_str}, notes={notes}")

        try:
            # Parse date from form - explicitly handle DD.MM.YYYY format
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
            logger.debug(f"Parsed visit date: {visit_date}")

            # Convert local date to UTC for storage
            from utils import from_local_timezone

            visit_date = from_local_timezone(visit_date)
            logger.debug(f"UTC visit date: {visit_date}")

            # Create new visit
            visit = HospitalVisit(visit_date=visit_date, notes=notes)

            db.session.add(visit)
            db.session.commit()

            logger.info(
                f"New hospital visit created: ID={visit.id}, date={visit_date_str}"
            )

            flash(f"Hospital visit scheduled for {visit_date_str}", "success")

            # Check if we should create an order automatically
            create_order = request.form.get("create_order", "no")
            if create_order == "yes":
                logger.debug(f"Redirecting to order creation for visit ID={visit.id}")
                return redirect(url_for("orders.new", visit_id=visit.id))
            else:
                logger.debug(f"Redirecting to visit details for visit ID={visit.id}")
                return redirect(url_for("visits.show", id=visit.id))

        except ValueError as e:
            logger.error(f"Date parsing error: {e} for input '{visit_date_str}'")
            flash("Invalid date format. Please use DD.MM.YYYY format.", "error")

    return render_template(
        "visits/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@visit_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific hospital visit."""
    logger.debug(f"Accessing visit details page for ID={id}")

    visit = HospitalVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    # Get orders for this visit
    orders = Order.query.filter_by(hospital_visit_id=visit.id).all()
    logger.debug(f"Found {len(orders)} orders for this visit")

    # Get all medications for medication needs calculation
    medications = Medication.query.all()
    medication_needs = {}

    for med in medications:
        if med.inventory:
            needed = med.calculate_needed_until_visit(visit.visit_date)
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

    logger.debug(f"Calculated needs for {len(medication_needs)} medications")

    return render_template(
        "visits/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        orders=orders,
        medication_needs=medication_needs,
    )


@visit_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing hospital visit."""
    logger.debug(f"Accessing edit page for visit ID={id}")

    visit = HospitalVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        logger.debug(f"Edit visit form data: date={visit_date_str}, notes={notes}")

        try:
            # Parse date from form
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
            logger.debug(f"Parsed visit date: {visit_date}")

            # Convert local date to UTC for storage
            from utils import from_local_timezone

            visit_date = from_local_timezone(visit_date)
            logger.debug(f"UTC visit date: {visit_date}")

            # Update visit
            visit.visit_date = visit_date
            visit.notes = notes

            db.session.commit()

            logger.info(
                f"Updated hospital visit: ID={visit.id}, new date={visit_date_str}"
            )

            flash(f"Hospital visit updated to {visit_date_str}", "success")
            return redirect(url_for("visits.show", id=visit.id))

        except ValueError as e:
            logger.error(f"Date parsing error: {e} for input '{visit_date_str}'")
            flash("Invalid date format. Please use DD.MM.YYYY format.", "error")

    # Format date for the form - use local timezone
    from utils import to_local_timezone

    local_visit_date = to_local_timezone(visit.visit_date)
    formatted_date = local_visit_date.strftime("%d.%m.%Y")
    logger.debug(f"Formatted date for form: {formatted_date}")

    return render_template(
        "visits/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        formatted_date=formatted_date,
    )


@visit_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a hospital visit."""
    logger.debug(f"Attempting to delete visit ID={id}")

    visit = HospitalVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    # Check if there are orders associated with this visit
    orders = Order.query.filter_by(hospital_visit_id=visit.id).all()
    if orders:
        logger.warning(
            f"Cannot delete visit ID={id} with {len(orders)} associated orders"
        )
        flash(
            "Cannot delete visit with associated orders. Delete the orders first.",
            "error",
        )
        return redirect(url_for("visits.show", id=visit.id))

    db.session.delete(visit)
    db.session.commit()

    logger.info(f"Deleted hospital visit: ID={id}")

    flash("Hospital visit deleted successfully", "success")
    return redirect(url_for("visits.index"))


@visit_bp.route("/next")
def next_visit():
    """Display details about the next upcoming hospital visit."""
    logger.debug("Accessing next visit redirect")

    next_visit = (
        HospitalVisit.query.filter(HospitalVisit.visit_date >= utcnow())
        .order_by(HospitalVisit.visit_date)
        .first()
    )

    if not next_visit:
        logger.info("No upcoming hospital visits found")
        flash("No upcoming hospital visits scheduled", "warning")
        return redirect(url_for("visits.new"))

    logger.debug(f"Redirecting to next visit ID={next_visit.id}")
    return redirect(url_for("visits.show", id=next_visit.id))
