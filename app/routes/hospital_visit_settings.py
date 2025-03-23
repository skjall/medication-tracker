"""
Routes for managing hospital visit settings.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from models import db
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
    return render_template("settings/advanced.html")
