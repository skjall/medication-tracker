"""
Routes for physician visit management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

# Local application imports
from models import PhysicianVisit, Medication, Order, Physician, db, utcnow
from utils import to_local_timezone, ensure_timezone_utc

# Get a logger specific to this module
logger = logging.getLogger(__name__)

# Create a blueprint for visit routes
visit_bp = Blueprint("visits", __name__, url_prefix="/physician_visits")


@visit_bp.route("/")
def index():
    """Display list of all physician visits."""
    # Log at various levels to demonstrate the system
    logger.debug("Accessing visits index page")
    logger.info(f"Current time (UTC): {utcnow()}")

    # Get upcoming visits - now using utcnow() from models
    upcoming_visits = (
        PhysicianVisit.query.filter(PhysicianVisit.visit_date >= utcnow())
        .order_by(PhysicianVisit.visit_date)
        .all()
    )

    logger.info(f"Found {len(upcoming_visits)} upcoming visits")
    logger.debug(f"Upcoming visits: {[visit.id for visit in upcoming_visits]}")

    # Get past visits
    past_visits = (
        PhysicianVisit.query.filter(PhysicianVisit.visit_date < utcnow())
        .order_by(PhysicianVisit.visit_date.desc())
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
    """Create a new physician visit."""
    logger.debug("Accessing new visit page")

    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        # Extract physician field
        physician_id = request.form.get("physician_id")
        if physician_id == "":
            physician_id = None
        elif physician_id:
            physician_id = int(physician_id)

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
            visit = PhysicianVisit(visit_date=visit_date, notes=notes, physician_id=physician_id)

            db.session.add(visit)
            db.session.commit()

            logger.info(
                f"New physician visit created: ID={visit.id}, date={visit_date_str}"
            )

            flash(_("Physician visit scheduled for {}").format(visit_date_str), "success")

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
            flash(_("Invalid date format. Please use DD.MM.YYYY format."), "error")

    physicians = Physician.query.order_by(Physician.name).all()
    return render_template(
        "visits/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        physicians=physicians,
    )


@visit_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific physician visit."""
    logger.debug(f"Accessing visit details page for ID={id}")

    visit = PhysicianVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    # Get orders for this visit
    orders = Order.query.filter_by(physician_visit_id=visit.id).all()
    logger.debug(f"Found {len(orders)} orders for this visit")

    # Get medications for this physician only (prescribed by this physician)
    if visit.physician_id:
        # Show ONLY medications explicitly prescribed by this specific physician
        medications = Medication.query.filter(
            Medication.physician_id == visit.physician_id
        ).all()
        logger.debug(f"Visit has physician_id={visit.physician_id}, showing {len(medications)} medications")
    else:
        # For visits without a physician, show only unassigned OTC medications
        medications = Medication.query.filter(
            (Medication.physician_id.is_(None)) & (Medication.is_otc.is_(True))
        ).all()
        logger.debug(f"Visit has no physician, showing {len(medications)} OTC medications only")
    
    medication_needs = {}

    for med in medications:
        if med.inventory:
            needed = med.calculate_needed_until_visit(visit.visit_date)
            current = med.total_inventory_count  # Use total including packages
            additional = max(0, needed - current)
            packages = med.calculate_packages_needed(additional)

            # Calculate if medication will run out before visit (without safety margin)
            # Use depletion_date which is based on current_count / daily_usage (no safety margin)
            will_deplete_before_visit = (
                med.depletion_date is not None and 
                ensure_timezone_utc(med.depletion_date) < ensure_timezone_utc(visit.visit_date)
            )
            
            # Calculate needed WITHOUT safety margin to determine if truly running out
            needed_without_margin = med.calculate_needed_until_visit(visit.visit_date, include_safety_margin=False)
            additional_without_margin = max(0, needed_without_margin - current)
            
            # Categorize: truly running out vs. in safety margin
            # If it needs additional WITHOUT margin = truly running out
            # If it will deplete but doesn't need additional WITHOUT margin = in safety margin
            is_truly_running_out = will_deplete_before_visit and additional_without_margin > 0
            is_in_safety_margin = will_deplete_before_visit and additional_without_margin == 0
            
            logger.info(f"Gap coverage check for {med.name}: current={current}, needed_without_margin={needed_without_margin}, additional_without_margin={additional_without_margin}, will_deplete={will_deplete_before_visit}, truly_running_out={is_truly_running_out}, in_safety_margin={is_in_safety_margin}")

            medication_needs[med.id] = {
                "medication": med,
                "needed_units": needed,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages,
                "will_deplete_before_visit": will_deplete_before_visit,
                "is_truly_running_out": is_truly_running_out,
                "is_in_safety_margin": is_in_safety_margin,
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
    """Edit an existing physician visit."""
    logger.debug(f"Accessing edit page for visit ID={id}")

    visit = PhysicianVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        # Extract physician field
        physician_id = request.form.get("physician_id")
        if physician_id == "":
            physician_id = None
        elif physician_id:
            physician_id = int(physician_id)

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
            visit.physician_id = physician_id

            db.session.commit()

            logger.info(
                f"Updated physician visit: ID={visit.id}, new date={visit_date_str}"
            )

            flash(_("Physician visit updated to {}").format(visit_date_str), "success")
            return redirect(url_for("visits.show", id=visit.id))

        except ValueError as e:
            logger.error(f"Date parsing error: {e} for input '{visit_date_str}'")
            flash(_("Invalid date format. Please use DD.MM.YYYY format."), "error")

    # Format date for the form - use local timezone
    from utils import to_local_timezone

    local_visit_date = to_local_timezone(visit.visit_date)
    formatted_date = local_visit_date.strftime("%Y-%m-%d")  # HTML date input format
    logger.debug(f"Formatted date for form: {formatted_date}")

    physicians = Physician.query.order_by(Physician.name).all()
    return render_template(
        "visits/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        formatted_date=formatted_date,
        physicians=physicians,
    )


@visit_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a physician visit."""
    logger.debug(f"Attempting to delete visit ID={id}")

    visit = PhysicianVisit.query.get_or_404(id)
    logger.debug(f"Found visit: date={visit.visit_date}")

    # Check if there are orders associated with this visit
    orders = Order.query.filter_by(physician_visit_id=visit.id).all()
    if orders:
        logger.warning(
            f"Cannot delete visit ID={id} with {len(orders)} associated orders"
        )
        flash(
            _("Cannot delete visit with associated orders. Delete the orders first."),
            "error",
        )
        return redirect(url_for("visits.show", id=visit.id))

    db.session.delete(visit)
    db.session.commit()

    logger.info(f"Deleted physician visit: ID={id}")

    flash(_("Physician visit deleted successfully"), "success")
    return redirect(url_for("visits.index"))


@visit_bp.route("/next")
def next_visit():
    """Display details about the next upcoming physician visit."""
    logger.debug("Accessing next visit redirect")

    next_visit = (
        PhysicianVisit.query.filter(PhysicianVisit.visit_date >= utcnow())
        .order_by(PhysicianVisit.visit_date)
        .first()
    )

    if not next_visit:
        logger.info("No upcoming physician visits found")
        flash(_("No upcoming physician visits scheduled"), "warning")
        return redirect(url_for("visits.new"))

    logger.debug(f"Redirecting to next visit ID={next_visit.id}")
    return redirect(url_for("visits.show", id=next_visit.id))
