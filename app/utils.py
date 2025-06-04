"""
Utility functions for the Medication Tracker application.
"""

# Standard library imports
import csv
import logging
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Dict, List, Optional, Tuple, TypeVar

# Third-party imports
from flask import Response, current_app

# Create a logger for this module
logger = logging.getLogger(__name__)

# Generic type for min_value function
T = TypeVar("T")


def min_value(a: T, b: T) -> T:
    """
    Return the minimum of two values.

    Args:
        a: First value
        b: Second value

    Returns:
        The minimum value
    """
    return min(a, b)


def make_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware by adding UTC timezone if needed.

    Args:
        dt: Datetime object that might be timezone-naive

    Returns:
        Timezone-aware datetime object (with UTC timezone)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def ensure_timezone_utc(dt: datetime) -> datetime:
    """
    Make sure datetime has timezone info, defaulting to UTC if none.

    Args:
        dt: The datetime object to ensure has timezone info

    Returns:
        Timezone-aware datetime object (with UTC timezone)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def calculate_days_until(target_date: datetime) -> int:
    """
    Calculate days until a target date.

    Args:
        target_date: The target date

    Returns:
        Number of days until the target date
    """
    # Ensure target date is timezone-aware
    target_date = make_aware(target_date)

    # Convert target date to local timezone for date comparison
    local_target = to_local_timezone(target_date)

    # Get current time in local timezone
    now_utc = datetime.now(timezone.utc)
    local_now = to_local_timezone(now_utc)

    # Compare dates only (not times)
    target_date_only = local_target.date()
    now_date_only = local_now.date()

    # Calculate the difference in days
    delta = target_date_only - now_date_only
    days_diff = delta.days

    return days_diff


def get_color_for_inventory_level(
    current_count: int, min_threshold: int, days_remaining: Optional[float]
) -> str:
    """
    Get a color code based on inventory level.

    Args:
        current_count: Current inventory count
        min_threshold: Minimum threshold
        days_remaining: Days of medication remaining

    Returns:
        CSS color class (text-danger, text-warning, text-success)
    """
    if current_count < min_threshold:
        return "text-danger"

    # If we have less than 30 days supply
    if days_remaining and days_remaining < 30:
        return "text-warning"

    return "text-success"


def export_data_to_csv(
    data_list: List[Dict], headers: List[str], filename: str
) -> Response:
    """
    Generic function to export data to CSV.

    Args:
        data_list: List of dictionaries containing data to export
        headers: List of header names
        filename: Name of the CSV file

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(headers)

    # Write data
    for row in data_list:
        writer.writerow([row.get(header, "") for header in headers])

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"},
    )

    return response


def create_database_backup() -> str:
    """
    Create a backup of the SQLite database file.

    Returns:
        Path to the backup file
    """
    import shutil
    from datetime import datetime

    # Get the database path from app config
    db_path = os.path.join(current_app.root_path, "data", "medication_tracker.db")

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(current_app.root_path, "data", "backups")

    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f"medication_tracker_backup_{timestamp}.db")

    # Create backup
    shutil.copy2(db_path, backup_path)

    return backup_path


def optimize_database() -> Tuple[bool, str]:
    """
    Optimize the SQLite database.

    Returns:
        Tuple of (success boolean, message)
    """
    import sqlite3

    db_path = os.path.join(current_app.root_path, "data", "medication_tracker.db")

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute VACUUM to rebuild the database file
        cursor.execute("VACUUM")

        # Execute ANALYZE to update statistics
        cursor.execute("ANALYZE")

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]

        conn.close()

        if integrity_result == "ok":
            return True, "Database optimized successfully"
        else:
            return (
                False,
                f"Database optimization completed but integrity check returned: {integrity_result}",
            )

    except Exception as e:
        return False, f"Error optimizing database: {str(e)}"


def get_application_timezone():
    """
    Get the application timezone from settings.

    Returns:
        pytz timezone object for the configured timezone
    """
    from models import Settings

    settings = Settings.get_settings()
    import pytz

    return pytz.timezone(settings.timezone_name)


def to_local_timezone(dt: datetime) -> datetime:
    """
    Convert UTC datetime to local application timezone.

    Args:
        dt: Datetime object in UTC

    Returns:
        Datetime object converted to local application timezone
    """
    if dt is None:
        return None
    # Ensure datetime is UTC
    dt = ensure_timezone_utc(dt)
    # Convert to local timezone
    return dt.astimezone(get_application_timezone())


def from_local_timezone(dt: datetime) -> datetime:
    """
    Convert local datetime to UTC for storage.

    Args:
        dt: Datetime object in local timezone

    Returns:
        Datetime object converted to UTC
    """
    if dt is None:
        return None
    # If datetime has no timezone, assume it's in local timezone
    if dt.tzinfo is None:
        local_tz = get_application_timezone()
        dt = local_tz.localize(dt)
    # Convert to UTC
    return dt.astimezone(timezone.utc)


def format_time(date: datetime) -> str:
    """
    Format a datetime object for display in local timezone.

    Args:
        date: The datetime object to format

    Returns:
        Formatted date string
    """
    date = to_local_timezone(date)
    return date.strftime("%H:%M:%S")


def format_date(date: datetime) -> str:
    """
    Format a datetime object for display in local timezone.

    Args:
        date: The datetime object to format

    Returns:
        Formatted date string
    """
    date = to_local_timezone(date)
    return date.strftime("%d.%m.%Y")


def format_datetime(date: datetime, show_seconds: bool = False) -> str:
    """
    Format a datetime object with time for display in local timezone.

    Args:
        date: The datetime object to format

    Returns:
        Formatted datetime string
    """
    date = to_local_timezone(date)

    if show_seconds:
        return date.strftime("%d.%m.%Y %H:%M:%S")

    return date.strftime("%d.%m.%Y %H:%M")
