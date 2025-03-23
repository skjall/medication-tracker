"""
Routes for managing hospital visit settings.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from models import db, Medication, MedicationSchedule, HospitalVisit, InventoryLog
from hospital_visit_utils import HospitalVisitSettings, calculate_days_between_visits

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/hospital_visits", methods=["GET", "POST"])
def hospital_visits():
    """
    Display and update hospital visit settings.
    """
    # Get current settings
    settings = HospitalVisitSettings.get_settings()

    if request.method == "POST":
        # Update settings from form
        settings.default_visit_interval = int(
            request.form.get("default_visit_interval", 90)
        )
        settings.auto_schedule_visits = "auto_schedule_visits" in request.form
        settings.default_order_for_next_but_one = (
            "default_order_for_next_but_one" in request.form
        )

        db.session.commit()

        flash("Hospital visit settings updated successfully", "success")
        return redirect(url_for("settings.hospital_visits"))

    # Calculate actual average interval for information purposes
    actual_interval = calculate_days_between_visits()

    return render_template(
        "settings/hospital_visits.html",
        settings=settings,
        actual_interval=actual_interval,
    )


@settings_bp.route("/update_visit_order_planning/<int:visit_id>", methods=["POST"])
def update_visit_order_planning(visit_id: int):
    """
    Update the order planning setting for a specific visit.
    """
    from models import HospitalVisit

    visit = HospitalVisit.query.get_or_404(visit_id)

    # Toggle the setting
    visit.order_for_next_but_one = not visit.order_for_next_but_one
    db.session.commit()

    if visit.order_for_next_but_one:
        message = "Orders for this visit will now be planned to last until the next-but-one visit"
    else:
        message = "Orders for this visit will now be planned to last until the next visit only"

    flash(message, "success")
    return redirect(url_for("visits.show", id=visit_id))


@settings_bp.route("/advanced", methods=["GET"])
def advanced():
    """
    Advanced settings page (e.g., backup/restore, system settings).
    """
    # Get hospital visit settings
    settings = HospitalVisitSettings.get_settings()

    # Get database statistics
    med_count = Medication.query.count()
    schedule_count = MedicationSchedule.query.count()
    upcoming_visits_count = HospitalVisit.query.filter(
        HospitalVisit.visit_date >= datetime.now(timezone.utc)
    ).count()

    # Get inventory logs count
    inventory_logs_count = InventoryLog.query.count()

    # Get database path for display
    db_path = os.path.join("data", "medication_tracker.db")

    # Get database size
    db_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
    db_size_mb = (
        round(os.path.getsize(db_file_path) / (1024 * 1024), 2)
        if os.path.exists(db_file_path)
        else 0
    )

    return render_template(
        "settings/advanced.html",
        settings=settings,
        med_count=med_count,
        schedule_count=schedule_count,
        upcoming_visits_count=upcoming_visits_count,
        inventory_logs_count=inventory_logs_count,
        db_path=db_path,
        db_size_mb=db_size_mb,
    )
