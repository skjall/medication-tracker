"""
Timezone helper module for the Medication Tracker application.

This module provides utility functions for timezone operations, including
conversion between UTC and local timezone, timezone validation, and
getting lists of common timezones.
"""

from typing import List, Dict
from datetime import datetime
import pytz
import logging

# Get module-specific logger
logger = logging.getLogger(__name__)


def get_common_timezones() -> List[str]:
    """
    Get a list of common timezones for display in the UI.

    Returns:
        List of timezone strings
    """
    try:
        timezones = sorted(pytz.common_timezones)
        logger.info(f"Found {len(timezones)} common timezones")
        return timezones
    except Exception as e:
        logger.error(f"Error getting common timezones: {e}")
        return []


def get_timezone_display_info() -> List[Dict[str, str]]:
    """
    Get timezone display information including region and current offset.

    Returns:
        List of dictionaries with timezone information
    """
    logger.info("Getting timezone display information")

    # Important: Use a naive datetime object (no timezone info)
    # This is required for pytz localization
    now_naive = datetime.now().replace(microsecond=0)

    timezone_info = []

    # Track how many timezones we're processing
    processed = 0
    skipped = 0

    for tz_name in get_common_timezones():
        try:
            processed += 1
            tz = pytz.timezone(tz_name)

            # Properly localize the naive datetime using pytz
            now_localized = tz.localize(now_naive)

            # Get UTC offset
            utc_offset = now_localized.utcoffset()
            offset_seconds = utc_offset.total_seconds()
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
                    "city": city.replace("_", " "),
                    "offset": offset_str,
                    "display_name": display_name,
                }
            )
        except Exception as e:
            skipped += 1
            logger.error(f"Error processing timezone {tz_name}: {e}")
            continue

    # Process special timezones
    # UTC and GMT are already in pytz.common_timezones, but let's make sure they're in our list
    for special_tz in ["UTC", "GMT"]:
        if not any(tz["name"] == special_tz for tz in timezone_info):
            timezone_info.append(
                {
                    "name": special_tz,
                    "region": "",
                    "city": special_tz,
                    "offset": "UTC+00:00",
                    "display_name": f"{special_tz} (UTC+00:00)",
                }
            )

    # Log the result
    logger.info(
        f"Processed {processed} timezones, skipped {skipped}, returning {len(timezone_info)} entries"
    )

    # Sort by region and then by city
    result = sorted(
        timezone_info, key=lambda x: (x.get("region", ""), x.get("city", ""))
    )

    # Log final count
    logger.info(f"Final timezone list contains {len(result)} entries")

    # Print first few entries as a sample
    for line_index, tz in enumerate(result[:5]):
        logger.debug(
            f"Sample timezone {line_index + 1}: {tz['name']} - {tz['display_name']}"
        )

    return result


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
