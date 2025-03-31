"""
Hospital Visit Settings and Automatic Deduction utilities.

This module provides:
1. Automatic inventory deduction process
2. Utility functions for visit planning
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple, Any
import logging

from sqlalchemy import func

from models import db, ensure_timezone_utc, utcnow, HospitalVisitSettings


def calculate_estimated_next_visit_date(from_date: datetime = None) -> datetime:
    """
    Calculate the estimated date of the next hospital visit based on settings.

    Args:
        from_date: The date to calculate from (defaults to current date)

    Returns:
        Estimated next visit date
    """
    if from_date is None:
        from_date = utcnow()
    else:
        from_date = ensure_timezone_utc(from_date)

    settings = HospitalVisitSettings.get_settings()

    # Calculate next visit date based on default interval
    next_visit_date = from_date + timedelta(days=settings.default_visit_interval)

    return next_visit_date


def calculate_days_between_visits() -> int:
    """
    Calculate the actual average days between visits based on historical data.
    Falls back to settings if not enough data.

    Returns:
        Average days between visits
    """
    from models import HospitalVisit

    # Get last 5 visits
    visits = (
        HospitalVisit.query.order_by(HospitalVisit.visit_date.desc()).limit(6).all()
    )

    # If we have at least 2 visits, calculate average
    if len(visits) >= 2:
        # Sort by date (oldest first)
        visits.sort(key=lambda v: v.visit_date)

        # Calculate differences - ensure all dates are timezone-aware
        intervals = []
        for i in range(1, len(visits)):
            v1_date = ensure_timezone_utc(visits[i - 1].visit_date)
            v2_date = ensure_timezone_utc(visits[i].visit_date)
            days = (v2_date - v1_date).days
            intervals.append(days)

        # Return average
        if intervals:
            return int(sum(intervals) / len(intervals))

    # Fallback to settings
    return HospitalVisitSettings.get_settings().default_visit_interval


def auto_deduct_inventory() -> int:
    """
    Check medications that are due for automatic deduction.
    Should be run regularly (e.g. every hour) to ensure timely deductions.

    Returns:
        Number of medications deducted
    """
    from models import Medication
    from utils import to_local_timezone, from_local_timezone

    logger = logging.getLogger(__name__)
    logger.info("Running automatic inventory deduction")

    current_time = utcnow()
    deduction_count = 0

    # Get settings
    settings = HospitalVisitSettings.get_settings()

    # Record that we checked
    settings.last_deduction_check = current_time
    db.session.commit()

    # Get all medications with auto-deduction enabled
    medications = Medication.query.filter_by(auto_deduction_enabled=True).all()

    logger.info(f"Checking {len(medications)} medications with auto-deduction enabled")

    # Process each medication
    for medication in medications:
        if not medication.inventory:
            logger.warning(f"Medication {medication.name} has no inventory record")
            continue

        # Check each schedule
        for schedule in medication.schedules:
            if schedule.is_due_now(current_time):
                logger.info(f"Schedule {schedule.id} for {medication.name} is due now")

                # Deduct the scheduled amount
                amount = schedule.units_per_dose
                if amount > 0 and medication.inventory.current_count >= amount:
                    medication.inventory.update_count(
                        -amount,
                        f"Automatic deduction: {amount} units at {current_time.strftime('%d.%m.%Y %H:%M')}",
                    )
                    deduction_count += 1

                    # Update last deduction time
                    schedule.last_deduction = current_time
                    logger.info(f"Deducted {amount} units from {medication.name}")
                else:
                    logger.warning(
                        f"Not enough inventory to deduct {amount} units from {medication.name}. Current count: {medication.inventory.current_count}"
                    )
            else:
                logger.info(
                    f"Schedule {schedule.id} for {medication.name} is not due yet."
                )

    # Commit all changes
    if deduction_count > 0:
        db.session.commit()
        logger.info(f"Auto-deduction complete: {deduction_count} medications deducted")
    else:
        logger.info("No medications due for deduction at this time")

    return deduction_count


class HospitalVisitSettings:
    """
    Helper class to access hospital visit settings.
    This is a facade to the database model for use in other modules.
    """

    @staticmethod
    def get_settings():
        """
        Get the application settings for hospital visits.

        Returns:
            Hospital visit settings object
        """
        from models import HospitalVisitSettings as SettingsModel

        return SettingsModel.get_settings()
