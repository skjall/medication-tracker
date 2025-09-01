"""
Routes for physician visit management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone, timedelta

# Third-party imports
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

# Local application imports
from models import PhysicianVisit, MedicationProduct, ActiveIngredient, Order, Physician, db, utcnow
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

    # Get products for this physician only (prescribed by this physician)
    if visit.physician_id:
        # Show ONLY products explicitly prescribed by this specific physician
        products = MedicationProduct.query.filter(
            MedicationProduct.physician_id == visit.physician_id
        ).order_by(MedicationProduct.brand_name).all()
        logger.debug(f"Visit has physician_id={visit.physician_id}, showing {len(products)} products")
    else:
        # For visits without a physician, show only OTC products
        products = MedicationProduct.query.filter(
            (MedicationProduct.physician_id.is_(None)) & (MedicationProduct.is_otc.is_(True))
        ).order_by(MedicationProduct.brand_name).all()
        logger.debug(f"Visit has no physician, showing {len(products)} OTC products only")
    
    product_needs = {}

    for product in products:
        # Get the active ingredient for this product
        ingredient = product.active_ingredient
        if ingredient:
            # Calculate current inventory from package inventory
            from models import PackageInventory, ScannedItem
            
            current = 0
            
            # Add package-based inventory
            package_inventories = PackageInventory.query.join(
                ScannedItem
            ).filter(
                ScannedItem.gtin.in_([pkg.gtin for pkg in product.packages if pkg.gtin]),
                PackageInventory.status.in_(['sealed', 'opened'])
            ).all()
            
            for inv in package_inventories:
                current += inv.current_units
            
            # Calculate days until visit
            days_until = (ensure_timezone_utc(visit.visit_date) - utcnow()).days
            
            # Get daily usage from medication schedule
            from models import MedicationSchedule, ScheduleType
            
            schedule = MedicationSchedule.query.filter_by(
                active_ingredient_id=ingredient.id
            ).first()
            
            daily_usage = 0
            if schedule:
                # Calculate daily usage based on schedule type
                if schedule.schedule_type == ScheduleType.DAILY:
                    daily_usage = schedule.units_per_dose
                elif schedule.schedule_type == ScheduleType.INTERVAL:
                    # Units per dose divided by interval days
                    daily_usage = schedule.units_per_dose / schedule.interval_days
                elif schedule.schedule_type == ScheduleType.WEEKDAYS:
                    # WEEKDAYS uses the weekdays field to determine which days
                    weekdays = schedule.weekdays or []
                    days_per_week = len(weekdays) if weekdays else 5
                    daily_usage = (schedule.units_per_dose * days_per_week) / 7
                
                logger.debug(f"Product {product.display_name}: schedule_type={schedule.schedule_type}, units_per_dose={schedule.units_per_dose}, daily_usage={daily_usage}")
            
            # Get safety margin from ingredient or use default
            safety_margin_days = getattr(ingredient, 'safety_margin_days', 7) or 7
            
            # Calculate needed units (with safety margin)
            needed = int(daily_usage * (days_until + safety_margin_days))
            
            # Calculate additional needed
            additional = max(0, needed - current)
            
            # Determine package recommendations
            packages_needed = {}
            if additional > 0:
                # Get available package sizes for this product
                available_packages = {pkg.package_size: pkg.quantity for pkg in product.packages}
                
                logger.debug(f"Product {product.display_name}: additional={additional}, available_packages={available_packages}")
                
                # Calculate optimal package combination
                remaining = additional
                for size in ['N3', 'N2', 'N1']:
                    if size in available_packages:
                        size_qty = available_packages[size]
                        
                        if size_qty > 0:
                            count = remaining // size_qty
                            if count > 0:
                                packages_needed[size] = count
                                remaining = remaining % size_qty
                                logger.debug(f"  {size}: {count} packages (qty={size_qty}), remaining={remaining}")
                
                # If there's still remaining, add one more of the smallest package
                if remaining > 0:
                    for size in ['N1', 'N2', 'N3']:
                        if size in available_packages:
                            packages_needed[size] = packages_needed.get(size, 0) + 1
                            logger.debug(f"  Adding 1 more {size} for remaining {remaining} units")
                            break
                
                logger.debug(f"  Final packages_needed: {packages_needed}")
            
            # Calculate depletion date if daily usage > 0
            will_deplete_before_visit = False
            depletion_date = None
            if daily_usage > 0 and current > 0:
                days_until_depletion = current / daily_usage
                depletion_date = utcnow() + timedelta(days=days_until_depletion)
                will_deplete_before_visit = depletion_date < ensure_timezone_utc(visit.visit_date)
            
            product_needs[product.id] = {
                "product": product,
                "ingredient": ingredient,
                "daily_usage": daily_usage,
                "safety_margin_days": safety_margin_days,
                "needed_units": needed,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages_needed,
                "will_deplete_before_visit": will_deplete_before_visit,
                "depletion_date": depletion_date
            }

    logger.debug(f"Calculated needs for {len(product_needs)} products")

    return render_template(
        "visits/show.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        visit=visit,
        orders=orders,
        product_needs=product_needs,
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
