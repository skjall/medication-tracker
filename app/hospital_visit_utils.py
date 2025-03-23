"""
Hospital Visit Settings and Automatic Deduction utilities.

This module provides:
1. Automatic inventory deduction background task
2. Utility functions for visit planning
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple, Any
import threading
import time
import logging

from flask import current_app
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


def auto_deduct_inventory():
    """
    Check medications that are due for automatic deduction.
    Should be run regularly (e.g. every hour) to ensure timely deductions.
    """
    from models import Medication
    from utils import to_local_timezone, from_local_timezone

    logging.info("Running automatic inventory deduction")

    current_time = utcnow()

    # Get settings
    settings = HospitalVisitSettings.get_settings()

    # Record that we checked
    settings.last_deduction_check = current_time
    db.session.commit()

    # Get all medications with auto-deduction enabled
    medications = Medication.query.filter_by(auto_deduction_enabled=True).all()

    for med in medications:
        # Check and deduct if scheduled
        deducted, amount = med.check_and_deduct_inventory(current_time)
        if deducted:
            logging.info(f"Auto-deducted {amount} units of {med.name}")

    # Commit all changes
    db.session.commit()


class AutoDeductionThread(threading.Thread):
    """
    Background thread to periodically check for and apply automatic inventory deductions.
    """

    def __init__(self, app, interval_seconds=3600):
        """
        Initialize the auto-deduction thread.

        Args:
            app: Flask application instance
            interval_seconds: How often to check for deductions (default: 1 hour)
        """
        super().__init__(daemon=True)
        self.app = app
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()

    def run(self):
        """Run the deduction thread until stopped."""
        logging.info("Starting automatic inventory deduction thread")

        while not self.stop_event.is_set():
            # Create app context for database operations
            with self.app.app_context():
                try:
                    auto_deduct_inventory()
                except Exception as e:
                    logging.error(f"Error in auto-deduction: {e}")

            # Sleep until next check
            time.sleep(self.interval_seconds)

    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()


def setup_auto_deduction(app, interval_seconds=3600):
    """
    Setup and start the automatic inventory deduction background task.

    Args:
        app: Flask application instance
        interval_seconds: How often to check for deductions (default: 1 hour)

    Returns:
        The started thread
    """
    thread = AutoDeductionThread(app, interval_seconds)
    thread.start()
    return thread
