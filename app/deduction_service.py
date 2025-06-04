"""
Enhanced medication deduction service.

This module provides improved medication deduction tracking, including:
1. Tracking missed deductions between scheduler runs
2. Proper handling of deduction timing
3. Retroactive application of deductions that should have happened
"""

# Standard library imports
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple

# Local application imports
from models import (
    Medication,
    MedicationSchedule,
    ScheduleType,
    db,
    ensure_timezone_utc,
    utcnow,
)
from utils import from_local_timezone, get_application_timezone, to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)


def get_and_fix_scheduled_times(schedule: MedicationSchedule) -> List[str]:
    """
    Get scheduled times from a medication schedule, detecting and fixing
    pipe-separated time formats that may exist in legacy data.

    Args:
        schedule: The medication schedule to get times from

    Returns:
        List of time strings in HH:MM format
    """
    try:
        # First, try to get times using the standard property
        times = schedule.formatted_times

        # Validate that all times are in correct HH:MM format
        for time_str in times:
            if not isinstance(time_str, str):
                logger.warning(f"Non-string time found in schedule {schedule.id}: {time_str}")
                continue

            # Check for pipe separator in individual time string (legacy data corruption)
            if '|' in time_str:
                logger.warning(f"Pipe-separated time detected in schedule {schedule.id}: {time_str}")

                # Split by pipe and fix the data
                pipe_split_times = time_str.split('|')

                # Validate each sub-time
                valid_times = []
                for sub_time in pipe_split_times:
                    sub_time = sub_time.strip()
                    if _validate_time_format(sub_time):
                        valid_times.append(sub_time)
                    else:
                        logger.error(f"Invalid time format after pipe split: {sub_time}")

                if valid_times:
                    # Fix the database entry
                    _fix_pipe_separated_times_in_db(schedule, valid_times)
                    return valid_times
                else:
                    logger.error(f"No valid times found after pipe split in schedule {schedule.id}")
                    return ["09:00"]  # Default fallback

            # Validate normal time format
            if not _validate_time_format(time_str):
                logger.error(f"Invalid time format in schedule {schedule.id}: {time_str}")
                continue

        return times

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing times for schedule {schedule.id}: {e}")

        # Try to access raw data and fix it
        raw_times = schedule.times_of_day
        logger.info(f"Raw times_of_day data: {raw_times}")

        if isinstance(raw_times, str):
            # Check if it's a pipe-separated string stored as a single item
            if '|' in raw_times:
                logger.warning(f"Pipe-separated times detected in raw data: {raw_times}")

                # Try to parse as a malformed JSON array with pipe-separated string
                try:
                    parsed = json.loads(raw_times)
                    if isinstance(parsed, list) and len(parsed) == 1 and '|' in parsed[0]:
                        # This is the case: ["08:00|12:00|18:00"]
                        pipe_separated_string = parsed[0]
                        times = pipe_separated_string.split('|')

                        # Validate each time
                        valid_times = []
                        for time_str in times:
                            time_str = time_str.strip()
                            if _validate_time_format(time_str):
                                valid_times.append(time_str)

                        if valid_times:
                            _fix_pipe_separated_times_in_db(schedule, valid_times)
                            return valid_times

                except json.JSONDecodeError:
                    # Raw string with pipes, not JSON
                    times = raw_times.split('|')
                    valid_times = []
                    for time_str in times:
                        time_str = time_str.strip()
                        if _validate_time_format(time_str):
                            valid_times.append(time_str)

                    if valid_times:
                        _fix_pipe_separated_times_in_db(schedule, valid_times)
                        return valid_times

        # Fallback for any parsing errors
        logger.error(f"Using fallback time for schedule {schedule.id}")
        return ["09:00"]


def _validate_time_format(time_str: str) -> bool:
    """
    Validate that a time string is in HH:MM format.

    Args:
        time_str: Time string to validate

    Returns:
        True if valid HH:MM format, False otherwise
    """
    if not isinstance(time_str, str):
        return False

    try:
        # Check basic format
        if ':' not in time_str:
            return False

        parts = time_str.split(':')
        if len(parts) != 2:
            return False

        hour, minute = parts
        hour_int = int(hour)
        minute_int = int(minute)

        # Validate ranges
        if not (0 <= hour_int <= 23):
            return False
        if not (0 <= minute_int <= 59):
            return False

        # Validate format (should be zero-padded)
        if len(hour) != 2 or len(minute) != 2:
            return False

        return True

    except (ValueError, IndexError):
        return False


def _fix_pipe_separated_times_in_db(schedule: MedicationSchedule, corrected_times: List[str]):
    """
    Fix pipe-separated times in the database by updating with proper JSON format.

    Args:
        schedule: The medication schedule to fix
        corrected_times: List of corrected time strings in HH:MM format
    """
    try:
        old_value = schedule.times_of_day
        new_value = json.dumps(corrected_times)

        logger.info(f"Fixing pipe-separated times in schedule {schedule.id}")
        logger.info(f"  Old value: {old_value}")
        logger.info(f"  New value: {new_value}")

        schedule.times_of_day = new_value
        db.session.commit()

        logger.info(f"Successfully fixed pipe-separated times for schedule {schedule.id}")

    except Exception as e:
        logger.error(f"Failed to fix pipe-separated times for schedule {schedule.id}: {e}")
        db.session.rollback()


def detect_pipe_separated_schedules() -> List[Tuple[int, str, str]]:
    """
    Detect all medication schedules with pipe-separated times.

    Returns:
        List of tuples (schedule_id, medication_name, problematic_times)
    """
    from models import MedicationSchedule

    logger.info("Scanning for medication schedules with pipe-separated times")

    problematic_schedules = []

    all_schedules = MedicationSchedule.query.all()

    for schedule in all_schedules:
        try:
            raw_times = schedule.times_of_day

            # Check for pipes in the raw data
            if isinstance(raw_times, str) and '|' in raw_times:
                medication_name = schedule.medication.name if schedule.medication else "Unknown"
                problematic_schedules.append((schedule.id, medication_name, raw_times))
                logger.warning(f"Found pipe-separated times in schedule {schedule.id} for {medication_name}: {raw_times}")

            # Also check parsed data for pipe-separated individual entries
            try:
                times = schedule.formatted_times
                for time_str in times:
                    if isinstance(time_str, str) and '|' in time_str:
                        medication_name = schedule.medication.name if schedule.medication else "Unknown"
                        problematic_schedules.append((schedule.id, medication_name, str(times)))
                        logger.warning(f"Found pipe in individual time for schedule {schedule.id}: {time_str}")
                        break
            except Exception:
                # If formatted_times fails, we already logged it above
                pass

        except Exception as e:
            logger.error(f"Error checking schedule {schedule.id}: {e}")

    logger.info(f"Scan complete. Found {len(problematic_schedules)} schedules with pipe-separated times")

    return problematic_schedules


def calculate_missed_deductions(
    schedule: MedicationSchedule, current_time: datetime
) -> List[datetime]:
    """
    Calculate missed deduction times since the last recorded deduction.

    Args:
        schedule: The medication schedule to check
        current_time: Current datetime (timezone-aware)

    Returns:
        List of datetime objects representing missed deductions
    """
    logger.debug(
        f"Calculating missed deductions for schedule {schedule.id} at {current_time.isoformat()}"
    )

    # Ensure times are timezone-aware
    current_time = ensure_timezone_utc(current_time)

    logger.debug(f"Current time after timezone utc check: {current_time.isoformat()}")

    # Convert to local time for schedule checking
    local_current_time = to_local_timezone(current_time)

    # Get the last deduction time or use a fallback
    if schedule.last_deduction:
        logger.debug(
            f"Last deduction time found: {schedule.last_deduction.isoformat()}"
        )

        last_deduction = ensure_timezone_utc(schedule.last_deduction)
        local_last_deduction = to_local_timezone(last_deduction)
    else:
        # If no deduction has been recorded yet, use created_at or a day ago
        if schedule.created_at:
            last_deduction = ensure_timezone_utc(schedule.created_at)
        else:
            # Fallback: one day ago
            last_deduction = current_time - timedelta(days=1)
        local_last_deduction = to_local_timezone(last_deduction)

    logger.info(
        f"Current time after timezone conversion to local: {local_current_time.isoformat()}"
    )

    # Get scheduled times in HH:MM format, with automatic pipe-separator fix
    scheduled_times = get_and_fix_scheduled_times(schedule)

    logger.debug(f"Scheduled times: {scheduled_times}")

    # Calculate missed deductions based on schedule type
    missed_deductions = []

    if str(schedule.schedule_type) == str(ScheduleType.DAILY):
        logger.debug("Calculating missed deductions for daily schedule")
        # For daily schedules, check each day between last deduction and now
        missed_deductions = _calculate_daily_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )

    elif str(schedule.schedule_type) == str(ScheduleType.INTERVAL):
        logger.debug("Calculating missed deductions for interval schedule")
        # For interval schedules (every X days)
        missed_deductions = _calculate_interval_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )

    elif str(schedule.schedule_type) == str(ScheduleType.WEEKDAYS):
        logger.debug("Calculating missed deductions for weekday schedule")
        # For specific weekdays
        missed_deductions = _calculate_weekdays_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )
    else:
        logger.warning(
            f"Unknown schedule type {schedule.schedule_type} for schedule {schedule.id}"
        )
        return []

    logger.info(f"Missed deductions calculated: {len(missed_deductions)} found")

    # Convert missed deductions back to UTC for database storage
    utc_missed_deductions = [from_local_timezone(dt) for dt in missed_deductions]

    logger.debug(f"Found {len(utc_missed_deductions)} missed deductions")

    if utc_missed_deductions:
        logger.info(
            f"Found {len(utc_missed_deductions)} missed deductions for schedule {schedule.id}"
        )
        for dt in utc_missed_deductions[:5]:  # Log first 5 only to avoid spam
            logger.debug(f"Missed deduction at: {dt.isoformat()}")
        if len(utc_missed_deductions) > 5:
            logger.debug(f"... and {len(utc_missed_deductions) - 5} more")

    return utc_missed_deductions


def _calculate_daily_missed_deductions(
    schedule: MedicationSchedule,
    local_last_deduction: datetime,
    local_current_time: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for daily schedules.

    Args:
        schedule: The medication schedule
        local_last_deduction: Last deduction time in local timezone
        local_current_time: Current time in local timezone
        scheduled_times: List of scheduled times (HH:MM format)

    Returns:
        List of missed deduction times in local timezone
    """
    # Ensure both times are timezone-aware in the application's timezone
    app_timezone = get_application_timezone()

    logger.debug(f"App timezone: {app_timezone}")

    # Make sure local_last_deduction and local_current_time are timezone-aware
    if local_last_deduction.tzinfo is None:
        local_last_deduction = local_last_deduction.replace(tzinfo=app_timezone)
    if local_current_time.tzinfo is None:
        local_current_time = local_current_time.replace(tzinfo=app_timezone)

    logger.debug(f"Local last deduction: {local_last_deduction.isoformat()}")

    missed_deductions = []

    # Get start and end dates (just the date part)
    start_date = local_last_deduction.date()
    end_date = local_current_time.date()

    # Track which time slots have already been processed for each day
    processed_slots = defaultdict(set)

    # If the last deduction was today, mark its time slot as processed
    if local_last_deduction.date() == local_current_time.date():
        time_str = local_last_deduction.strftime("%H:%M")
        # Find closest time slot
        for scheduled_time in scheduled_times:
            if (
                abs(
                    (
                        datetime.strptime(time_str, "%H:%M")
                        - datetime.strptime(scheduled_time, "%H:%M")
                    ).total_seconds()
                )
                < 300
            ):  # Within 5 minutes
                processed_slots[local_last_deduction.date()].add(scheduled_time)
                break

    # Iterate through each day from last deduction to current time
    current_date = start_date
    while current_date <= end_date:
        logger.debug(
            f"Processing date: {current_date.isoformat()} until {end_date.isoformat()}"
        )
        for time_str in scheduled_times:
            logger.debug(f"Checking time slot: {time_str}")

            # Skip if this time slot was already processed for this day
            if time_str in processed_slots[current_date]:
                logger.debug(
                    f"Time slot {time_str} already processed for {current_date}"
                )
                continue

            # Parse the time and create a timezone-aware datetime
            hour, minute = map(int, time_str.split(":"))
            scheduled_datetime = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                hour,
                minute,
                0,
                tzinfo=app_timezone,
            )

            # Only include times that are:
            # 1. After the last deduction
            # 2. Before the current time
            if (
                scheduled_datetime > local_last_deduction
                and scheduled_datetime <= local_current_time
            ):
                missed_deductions.append(scheduled_datetime)
            elif scheduled_datetime <= local_last_deduction:
                logger.debug(
                    f"Skipping time {scheduled_datetime.isoformat()} as it's before last deduction"
                )
            else:
                logger.debug(
                    f"Skipping time {scheduled_datetime.isoformat()} as it's after current time"
                )

        # Move to next day
        current_date += timedelta(days=1)

    return missed_deductions


def _calculate_interval_missed_deductions(
    schedule: MedicationSchedule,
    local_last_deduction: datetime,
    local_current_time: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for interval schedules (every X days).

    Args:
        schedule: The medication schedule
        local_last_deduction: Last deduction time in local timezone
        local_current_time: Current time in local timezone
        scheduled_times: List of scheduled times (HH:MM format)

    Returns:
        List of missed deduction times in local timezone
    """
    missed_deductions = []
    interval_days = schedule.interval_days

    # Ensure both times are timezone-aware in the application's timezone
    app_timezone = get_application_timezone()

    # Calculate the first day in the interval after the last deduction
    last_deduction_date = local_last_deduction.date()
    current_date = local_current_time.date()

    # Calculate days since last deduction
    days_since_last = (current_date - last_deduction_date).days

    # Calculate how many interval periods have passed
    intervals_passed = days_since_last // interval_days

    # If no full intervals have passed, there are no missed deductions
    if intervals_passed == 0:
        return []

    # Generate dates for each interval
    interval_dates = []
    for i in range(1, intervals_passed + 1):
        interval_date = last_deduction_date + timedelta(days=i * interval_days)
        # Stop if we exceed the current date
        if interval_date > current_date:
            break
        interval_dates.append(interval_date)

    # For each interval date, check all scheduled times
    for date in interval_dates:
        for time_str in scheduled_times:
            hour, minute = map(int, time_str.split(":"))
            scheduled_datetime = datetime(
                date.year,
                date.month,
                date.day,
                hour,
                minute,
                0,
                tzinfo=app_timezone,
            )

            # Only include times before current time
            if scheduled_datetime <= local_current_time:
                missed_deductions.append(scheduled_datetime)

    return missed_deductions


def _calculate_weekdays_missed_deductions(
    schedule: MedicationSchedule,
    local_last_deduction: datetime,
    local_current_time: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for weekday schedules.

    Args:
        schedule: The medication schedule
        local_last_deduction: Last deduction time in local timezone
        local_current_time: Current time in local timezone
        scheduled_times: List of scheduled times (HH:MM format)

    Returns:
        List of missed deduction times in local timezone
    """
    missed_deductions = []
    selected_weekdays = schedule.formatted_weekdays

    # Ensure both times are timezone-aware in the application's timezone
    app_timezone = get_application_timezone()

    # Get start and end dates
    start_date = local_last_deduction.date()
    end_date = local_current_time.date()

    # Track which time slots have already been processed for each day
    processed_slots = defaultdict(set)

    # If the last deduction was today and today is a selected weekday,
    # mark its time slot as processed
    if (
        local_last_deduction.date() == local_current_time.date()
        and local_last_deduction.weekday() in selected_weekdays
    ):
        time_str = local_last_deduction.strftime("%H:%M")
        # Find closest time slot
        for scheduled_time in scheduled_times:
            if (
                abs(
                    (
                        datetime.strptime(time_str, "%H:%M")
                        - datetime.strptime(scheduled_time, "%H:%M")
                    ).total_seconds()
                )
                < 300
            ):  # Within 5 minutes
                processed_slots[local_last_deduction.date()].add(scheduled_time)
                break

    # Iterate through each day from last deduction to current time
    current_date = start_date
    while current_date <= end_date:
        # Only process if this is a selected weekday
        if current_date.weekday() in selected_weekdays:
            for time_str in scheduled_times:
                # Skip if this time slot was already processed for this day
                if time_str in processed_slots[current_date]:
                    continue

                # Parse the time
                hour, minute = map(int, time_str.split(":"))
                scheduled_datetime = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    hour,
                    minute,
                    0,
                    tzinfo=app_timezone,
                )

                # Only include times that are:
                # 1. After the last deduction
                # 2. Before the current time
                if (
                    scheduled_datetime > local_last_deduction
                    and scheduled_datetime <= local_current_time
                ):
                    missed_deductions.append(scheduled_datetime)

        # Move to next day
        current_date += timedelta(days=1)

    return missed_deductions


def perform_deductions(current_time: datetime = None) -> Tuple[int, int]:
    """
    Perform all pending deductions including missed ones.

    Args:
        current_time: Optional override for current time (for testing)

    Returns:
        Tuple of (number of medications deducted, number of deduction actions)
    """
    if current_time is None:
        current_time = utcnow()
    else:
        current_time = ensure_timezone_utc(current_time)

    logger.info(f"Running medication deduction service at {current_time.isoformat()}")

    # Get all medications with auto-deduction enabled
    medications = Medication.query.filter_by(auto_deduction_enabled=True).all()

    logger.info(f"Checking {len(medications)} medications with auto-deduction enabled")

    med_count = 0  # Number of medications that had deductions
    action_count = 0  # Total number of deduction actions performed

    for medication in medications:
        if not medication.inventory:
            logger.warning(f"Medication {medication.name} has no inventory record")
            continue

        med_deducted = False

        # Check each schedule
        for schedule in medication.schedules:
            # First, calculate any missed deductions
            missed_deductions = calculate_missed_deductions(schedule, current_time)

            # If we have missed deductions, apply them
            if missed_deductions:
                logger.info(
                    f"Applying {len(missed_deductions)} missed deductions for {medication.name}"
                )

                # Sort by timestamp to apply them in chronological order
                missed_deductions.sort()

                for deduction_time in missed_deductions:
                    # Deduct the scheduled amount
                    amount = schedule.units_per_dose
                    if amount > 0 and medication.inventory.current_count >= amount:
                        medication.inventory.update_count(
                            -amount,
                            f"Automatic deduction (retroactive): {amount} units \
                                for {deduction_time.strftime('%d.%m.%Y %H:%M')}",
                        )
                        action_count += 1
                        med_deducted = True

                        logger.info(
                            f"Retroactively deducted {amount} units from {medication.name} for {deduction_time.isoformat()}"
                        )
                    else:
                        logger.warning(
                            f"Not enough inventory to deduct {amount} units from \
                                {medication.name}. Current count: {medication.inventory.current_count}"
                        )

                # Update last deduction time to the most recent missed deduction
                # only if we've actually deducted something
                if med_deducted and missed_deductions:
                    schedule.last_deduction = missed_deductions[-1]
            else:
                logger.debug(
                    f"No missed deductions for {medication.name} on schedule {schedule.id}"
                )

        # Count the medication if any of its schedules had deductions
        if med_deducted:
            med_count += 1

    # Commit all changes
    if action_count > 0:
        db.session.commit()
        logger.info(
            f"Deduction service complete: {action_count} deductions across {med_count} medications"
        )
    else:
        logger.info("No deductions needed at this time")

    # Update the last deduction check time in settings
    from models import Settings

    settings = Settings.get_settings()
    settings.last_deduction_check = current_time
    db.session.commit()

    return med_count, action_count
