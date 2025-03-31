"""
Hospital Visit Settings and Automatic Deduction utilities.

This module provides:
1. Automatic inventory deduction process
2. Utility functions for visit planning
"""

from __future__ import annotations
from datetime import datetime, timedelta
import logging

from models import ensure_timezone_utc, utcnow, Settings

# Logger for this module
logger = logging.getLogger(__name__)


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

    settings = Settings.get_settings()

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
    logger.info("Calculating average days between hospital visits")

    from models import HospitalVisit

    # Get last 5 visits
    visits = (
        HospitalVisit.query.order_by(HospitalVisit.visit_date.desc()).limit(6).all()
    )

    logger.info(f"Found {len(visits)} visits for calculation")

    # Iterate over visits if exist and show content of object
    for visit in visits:
        for key, value in visit.__dict__.items():
            if key != "_sa_instance_state":
                logger.debug(f"{key}: {value}")

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

        logger.info(f"Intervals: {intervals}")

        # Calculate average
        average = sum(intervals) / len(intervals)
        logger.info(f"Average days between visits: {average}")

        # Return average
        if intervals:
            return int(average)

    # Fallback to settings
    return Settings.get_settings().default_visit_interval


def auto_deduct_inventory() -> int:
    """
    Check medications that are due for automatic deduction.
    Should be run regularly (e.g. every hour) to ensure timely deductions.

    This function now uses the enhanced deduction service that properly
    handles missed deductions between scheduler runs.

    Returns:
        Number of medications deducted
    """
    logger.info("Running automatic inventory deduction (enhanced version)")

    # Import the enhanced deduction service
    from deduction_service import perform_deductions

    # Perform deductions and get results
    med_count, action_count = perform_deductions()

    # Return the count of medications affected
    return med_count
