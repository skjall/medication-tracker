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

# Local application imports
from models import (
    Medication,
    MedicationSchedule,
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
    Display all schedules for a specific medication.
    """
    medication = Medication.query.get_or_404(medication_id)
    return render_template(
        "schedules/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medication=medication,
        schedules=medication.schedules,
    )


@schedule_bp.route("/medication/<int:medication_id>/new", methods=["GET", "POST"])
def new(medication_id: int):
    """
    Create a new medication schedule.
    """
    medication = Medication.query.get_or_404(medication_id)

    if request.method == "POST":
        # Get basic schedule info
        schedule_type_str = request.form.get("schedule_type", "daily")
        schedule_type = ScheduleType(schedule_type_str)
        units_per_dose = float(request.form.get("units_per_dose", 1.0))

        # Parse times of day (array of HH:MM values)
        times_of_day = request.form.getlist("times_of_day[]")
        if not times_of_day:
            flash("Please add at least one time for the medication", "error")
            return render_template(
                "schedules/new.html",
                local_time=to_local_timezone(datetime.now(timezone.utc)),
                medication=medication,
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
            medication_id=medication.id,
            schedule_type=schedule_type,
            interval_days=interval_days,
            weekdays=json.dumps(weekdays) if weekdays else None,
            times_of_day=json.dumps(times_of_day),
            units_per_dose=units_per_dose,
        )

        db.session.add(schedule)
        db.session.commit()

        flash("Schedule added successfully", "success")
        return redirect(url_for("schedules.index", medication_id=medication.id))

    return render_template(
        "schedules/new.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medication=medication,
    )


@schedule_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """
    Edit an existing medication schedule.
    """
    schedule = MedicationSchedule.query.get_or_404(id)
    medication = schedule.medication

    if request.method == "POST":
        # Get basic schedule info
        schedule_type_str = request.form.get("schedule_type", "daily")
        schedule.schedule_type = ScheduleType(schedule_type_str)
        schedule.units_per_dose = float(request.form.get("units_per_dose", 1.0))

        # Parse times of day
        times_of_day = request.form.getlist("times_of_day[]")
        if not times_of_day:
            flash("Please add at least one time for the medication", "error")
            return render_template(
                "schedules/edit.html",
                local_time=to_local_timezone(datetime.now(timezone.utc)),
                medication=medication,
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

        flash("Schedule updated successfully", "success")
        return redirect(url_for("schedules.index", medication_id=medication.id))

    return render_template(
        "schedules/edit.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        medication=medication,
        schedule=schedule,
    )


@schedule_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """
    Delete a medication schedule.
    """
    schedule = MedicationSchedule.query.get_or_404(id)
    medication_id = schedule.medication_id

    db.session.delete(schedule)
    db.session.commit()

    flash("Schedule deleted successfully", "success")
    return redirect(url_for("schedules.index", medication_id=medication_id))


@schedule_bp.route(
    "/medication/<int:medication_id>/toggle_auto_deduction", methods=["POST"]
)
def toggle_auto_deduction(medication_id: int):
    """
    Toggle automatic inventory deduction for a medication.
    """
    medication = Medication.query.get_or_404(medication_id)

    medication.auto_deduction_enabled = not medication.auto_deduction_enabled
    db.session.commit()

    status = "enabled" if medication.auto_deduction_enabled else "disabled"
    flash(f"Automatic deduction {status} for {medication.name}", "success")

    return redirect(url_for("medications.show", id=medication_id))


@schedule_bp.route("/check_deductions", methods=["GET"])
def check_deductions():
    """
    Manually trigger the deduction check for all medications.
    For testing/debugging purposes.
    """
    from hospital_visit_utils import auto_deduct_inventory

    auto_deduct_inventory()
    flash("Medication deductions checked successfully", "success")

    # Get the referer to return to the previous page
    referer = request.headers.get("Referer")
    if referer and "system/status" in referer:
        return redirect(url_for("system.status"))

    return redirect(url_for("index"))
