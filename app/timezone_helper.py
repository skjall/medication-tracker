"""
Timezone helper module for the Medication Tracker application.

This module provides utility functions for timezone operations, including
conversion between UTC and local timezone, timezone validation, and
getting lists of common timezones.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
import pytz


def get_common_timezones() -> List[str]:
    """
    Get a list of common timezones for display in the UI.

    Returns:
        List of timezone strings
    """
    common_timezones = [
        "UTC",
        # Europe
        "Europe/Amsterdam",
        "Europe/Berlin",
        "Europe/London",
        "Europe/Madrid",
        "Europe/Moscow",
        "Europe/Paris",
        "Europe/Rome",
        "Europe/Vienna",
        # North America
        "US/Eastern",
        "US/Central",
        "US/Mountain",
        "US/Pacific",
        # Asia
        "Asia/Dubai",
        "Asia/Hong_Kong",
        "Asia/Jerusalem",
        "Asia/Shanghai",
        "Asia/Singapore",
        "Asia/Tokyo",
        # Australia/Oceania
        "Australia/Sydney",
        "Australia/Melbourne",
        "Pacific/Auckland",
        # South America
        "America/Bogota",
        "America/Buenos_Aires",
        "America/Sao_Paulo",
        # Africa
        "Africa/Cairo",
        "Africa/Johannesburg",
        "Africa/Lagos",
    ]

    return sorted(common_timezones)


def get_timezone_display_info() -> List[Dict[str, str]]:
    """
    Get timezone display information including region and current offset.

    Returns:
        List of dictionaries with timezone information
    """
    now = datetime.now(timezone.utc)
    timezone_info = []

    for tz_name in get_common_timezones():
        try:
            tz = pytz.timezone(tz_name)
            offset_seconds = tz.utcoffset(now).total_seconds()
            offset_hours = int(offset_seconds / 3600)
            offset_minutes = int((offset_seconds % 3600) / 60)

            # Format: "UTC+01:00" or "UTC-08:00"
            offset_str = f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:02d}:{abs(offset_minutes):02d}"

            # Split timezone name into region/city
            parts = tz_name.split("/")
            region = parts[0] if len(parts) > 0 else ""
            city = parts[1] if len(parts) > 1 else tz_name

            display_name = f"{city.replace('_', ' ')} ({offset_str})"

            timezone_info.append(
                {
                    "name": tz_name,
                    "region": region,
                    "city": city,
                    "offset": offset_str,
                    "display_name": display_name,
                }
            )
        except Exception:
            # Skip invalid timezones
            continue

    # Sort by region then offset
    return sorted(timezone_info, key=lambda x: (x["region"], x["offset"]))


def validate_timezone(timezone_name: str) -> bool:
    """
    Validate if a timezone name is valid.

    Args:
        timezone_name: Name of timezone to validate

    Returns:
        True if timezone is valid, False otherwise
    """
    try:
        pytz.timezone(timezone_name)
        return True
    except Exception:
        return False
