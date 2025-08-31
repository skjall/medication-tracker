"""
Routes for medication scheduling.
"""

# Standard library imports
import json
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
    ActiveIngredient,
    MedicationSchedule,
    MedicationProduct,
    ScheduleType,
    db,
)
from utils import to_local_timezone


# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for schedule routes
schedule_bp = Blueprint("schedules", __name__, url_prefix="/schedules")


@schedule_bp.route("/medication/<int:medication_id>")
def index(medication_id: int):
    """
    Redirect medication schedules to ingredient schedules.
    """
    # Find the product linked to this legacy medication
    product = MedicationProduct.query.filter_by(legacy_medication_id=medication_id).first()
    
    if product and product.active_ingredient_id:
        return redirect(url_for("schedules.index_ingredient", ingredient_id=product.active_ingredient_id))
    else:
        flash(_("This medication has not been migrated to the new system yet."), "warning")
        return redirect(url_for("ingredients.index"))


@schedule_bp.route("/medication/<int:medication_id>/new", methods=["GET", "POST"])
def new(medication_id: int):
    """
    Redirect to ingredient schedule creation.
    """
    # Find the product linked to this legacy medication
    product = MedicationProduct.query.filter_by(legacy_medication_id=medication_id).first()
    
    if product and product.active_ingredient_id:
        return redirect(url_for("schedules.new_ingredient", ingredient_id=product.active_ingredient_id))
    else:
        flash(_("This medication has not been migrated to the new system yet."), "warning")
        return redirect(url_for("ingredients.index"))


@schedule_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """
    Edit an existing medication schedule.
    Works for both medication and ingredient schedules.
    """
    schedule = MedicationSchedule.query.get_or_404(id)
    
    # Prefer ingredient-based editing
    if schedule.active_ingredient:
        ingredient = schedule.active_ingredient
        
        if request.method == "POST":
            # Get basic schedule info
            schedule_type_str = request.form.get("schedule_type", "daily")
            schedule.schedule_type = ScheduleType(schedule_type_str)
            schedule.units_per_dose = float(request.form.get("units_per_dose", 1.0))

            # Parse times of day
            times_of_day = request.form.getlist("times_of_day[]")
            if not times_of_day:
                flash(_("Please add at least one time for the medication"), "error")
                return render_template(
                    "schedules/edit_ingredient.html",
                    local_time=to_local_timezone(datetime.now(timezone.utc)),
                    ingredient=ingredient,
                    schedule=schedule,
                )

            schedule.times_of_day = json.dumps(times_of_day)

            # Process schedule-specific data
            if schedule.schedule_type == ScheduleType.INTERVAL:
                schedule.interval_days = int(request.form.get("interval_days", 1))
                if schedule.interval_days < 1:
                    schedule.interval_days = 1

            elif schedule.schedule_type == ScheduleType.WEEKDAYS:
                weekdays = request.form.getlist("weekdays[]")
                weekdays = [int(day) for day in weekdays]
                schedule.weekdays = json.dumps(weekdays) if weekdays else None

            # Save changes
            db.session.commit()

            flash(_("Schedule updated successfully"), "success")
            return redirect(url_for("schedules.index_ingredient", ingredient_id=ingredient.id))

        return render_template(
            "schedules/edit_ingredient.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            ingredient=ingredient,
            schedule=schedule,
        )
    
    # Fallback: redirect to ingredient if possible
    elif schedule.medication:
        product = MedicationProduct.query.filter_by(legacy_medication_id=schedule.medication_id).first()
        if product and product.active_ingredient_id:
            # Migrate this schedule to use ingredient
            schedule.active_ingredient_id = product.active_ingredient_id
            schedule.medication_id = None
            db.session.commit()
            return redirect(url_for("schedules.edit", id=id))
    
    flash(_("Cannot edit this schedule - migration required."), "error")
    return redirect(url_for("ingredients.index"))


@schedule_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """
    Delete a medication schedule.
    """
    schedule = MedicationSchedule.query.get_or_404(id)
    
    # Determine where to redirect
    redirect_url = url_for("ingredients.index")
    if schedule.active_ingredient_id:
        redirect_url = url_for("schedules.index_ingredient", ingredient_id=schedule.active_ingredient_id)
    elif schedule.medication_id:
        product = MedicationProduct.query.filter_by(legacy_medication_id=schedule.medication_id).first()
        if product and product.active_ingredient_id:
            redirect_url = url_for("schedules.index_ingredient", ingredient_id=product.active_ingredient_id)

    db.session.delete(schedule)
    db.session.commit()

    flash(_("Schedule deleted successfully"), "success")
    return redirect(redirect_url)


@schedule_bp.route(
    "/medication/<int:medication_id>/toggle_auto_deduction", methods=["POST"]
)
def toggle_auto_deduction(medication_id: int):
    """
    Redirect medication auto-deduction to ingredient.
    """
    # Find the product linked to this legacy medication
    product = MedicationProduct.query.filter_by(legacy_medication_id=medication_id).first()
    
    if product and product.active_ingredient_id:
        return redirect(url_for("schedules.toggle_auto_deduction_ingredient", ingredient_id=product.active_ingredient_id))
    else:
        flash(_("This medication has not been migrated to the new system yet."), "warning")
        return redirect(url_for("ingredients.index"))


@schedule_bp.route("/check_deductions", methods=["GET"])
def check_deductions():
    """
    Manually trigger the deduction check for all medications.
    For testing/debugging purposes.
    """
    from physician_visit_utils import auto_deduct_inventory

    auto_deduct_inventory()
    flash(_("Medication deductions checked successfully"), "success")

    # Get the referer to return to the previous page
    referer = request.headers.get("Referer")
    if referer and "system/status" in referer:
        return redirect(url_for("system.status"))

    return redirect(url_for("index"))


# ============== NEW ACTIVE INGREDIENT ROUTES ==============

@schedule_bp.route("/ingredient/<int:ingredient_id>")
def index_ingredient(ingredient_id: int):
    """
    Display all schedules for a specific active ingredient.
    """
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)
    return render_template(
        "schedules/index_ingredient.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        ingredient=ingredient,
        schedules=ingredient.schedules,
    )


@schedule_bp.route("/ingredient/<int:ingredient_id>/new", methods=["GET", "POST"])
def new_ingredient(ingredient_id: int):
    """
    Create a new schedule for an active ingredient.
    """
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)

    if request.method == "POST":
        # Get basic schedule info
        schedule_type_str = request.form.get("schedule_type", "daily")
        schedule_type = ScheduleType(schedule_type_str)
        units_per_dose = float(request.form.get("units_per_dose", 1.0))

        # Parse times of day (array of HH:MM values)
        times_of_day = request.form.getlist("times_of_day[]")
        if not times_of_day:
            flash(_("Please add at least one time for the medication"), "error")
            return render_template(
                "schedules/new_ingredient.html",
                local_time=to_local_timezone(datetime.now(timezone.utc)),
                ingredient=ingredient,
            )

        # Process schedule-specific data
        interval_days = 1
        weekdays = []

        if schedule_type == ScheduleType.INTERVAL:
            interval_days = int(request.form.get("interval_days", 1))
            if interval_days < 1:
                interval_days = 1

        elif schedule_type == ScheduleType.WEEKDAYS:
            weekdays = request.form.getlist("weekdays[]")
            weekdays = [int(day) for day in weekdays]

        # Create schedule
        schedule = MedicationSchedule(
            active_ingredient_id=ingredient.id,
            schedule_type=schedule_type,
            interval_days=interval_days,
            weekdays=json.dumps(weekdays) if weekdays else None,
            times_of_day=json.dumps(times_of_day),
            units_per_dose=units_per_dose,
        )

        db.session.add(schedule)
        db.session.commit()

        flash(_("Schedule added successfully"), "success")
        return redirect(url_for("schedules.index_ingredient", ingredient_id=ingredient.id))

    return render_template(
        "schedules/new_ingredient.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        ingredient=ingredient,
    )


@schedule_bp.route("/ingredient/<int:ingredient_id>/toggle_auto_deduction", methods=["POST"])
def toggle_auto_deduction_ingredient(ingredient_id: int):
    """
    Toggle automatic inventory deduction for an active ingredient.
    When enabling, records the timestamp to prevent retroactive deductions before this point.
    """
    from models import utcnow
    import logging
    
    logger = logging.getLogger(__name__)
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)

    ingredient.auto_deduction_enabled = not ingredient.auto_deduction_enabled
    
    # When enabling auto-deduction, record the timestamp
    # This prevents retroactive deductions for periods when it was disabled
    if ingredient.auto_deduction_enabled:
        ingredient.auto_deduction_enabled_at = utcnow()
        logger.info(f"Auto-deduction enabled for {ingredient.name} at {ingredient.auto_deduction_enabled_at}")
    else:
        # Optionally clear the timestamp when disabling, or keep it for history
        # We'll keep it for history - it will be updated next time it's enabled
        logger.info(f"Auto-deduction disabled for {ingredient.name}")
    
    db.session.commit()

    status = "enabled" if ingredient.auto_deduction_enabled else "disabled"
    flash(_("Automatic deduction {} for {}").format(status, ingredient.name), "success")

    return redirect(url_for("ingredients.show", id=ingredient_id))
