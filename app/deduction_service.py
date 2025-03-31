"""
Enhanced medication deduction service.

This module provides improved medication deduction tracking, including:
1. Tracking missed deductions between scheduler runs
2. Proper handling of deduction timing
3. Retroactive application of deductions that should have happened
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Any
import logging
from collections import defaultdict
from utils import get_application_timezone

from models import (
    db,
    Medication,
    MedicationSchedule,
    ScheduleType,
    ensure_timezone_utc,
    utcnow,
)
from utils import to_local_timezone, from_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)


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
    # Ensure times are timezone-aware
    current_time = ensure_timezone_utc(current_time)

    # Convert to local time for schedule checking
    local_current_time = to_local_timezone(current_time)

    # Get the last deduction time or use a fallback
    if schedule.last_deduction:
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

    logger.debug(
        f"Checking for missed deductions since {local_last_deduction.isoformat()}"
    )

    # Get scheduled times in HH:MM format
    scheduled_times = schedule.formatted_times

    # Calculate missed deductions based on schedule type
    missed_deductions = []

    if schedule.schedule_type == ScheduleType.DAILY:
        # For daily schedules, check each day between last deduction and now
        missed_deductions = _calculate_daily_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )

    elif schedule.schedule_type == ScheduleType.INTERVAL:
        # For interval schedules (every X days)
        missed_deductions = _calculate_interval_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )

    elif schedule.schedule_type == ScheduleType.WEEKDAYS:
        # For specific weekdays
        missed_deductions = _calculate_weekdays_missed_deductions(
            schedule, local_last_deduction, local_current_time, scheduled_times
        )

    # Convert missed deductions back to UTC for database storage
    utc_missed_deductions = [from_local_timezone(dt) for dt in missed_deductions]

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

    # Make sure local_last_deduction and local_current_time are timezone-aware
    if local_last_deduction.tzinfo is None:
        local_last_deduction = local_last_deduction.replace(tzinfo=app_timezone)
    if local_current_time.tzinfo is None:
        local_current_time = local_current_time.replace(tzinfo=app_timezone)

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
        for time_str in scheduled_times:
            # Skip if this time slot was already processed for this day
            if time_str in processed_slots[current_date]:
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
                            f"Automatic deduction (retroactive): {amount} units for {deduction_time.strftime('%d.%m.%Y %H:%M')}",
                        )
                        action_count += 1
                        med_deducted = True

                        logger.info(
                            f"Retroactively deducted {amount} units from {medication.name} for {deduction_time.isoformat()}"
                        )
                    else:
                        logger.warning(
                            f"Not enough inventory to deduct {amount} units from {medication.name}. Current count: {medication.inventory.current_count}"
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
    from models import HospitalVisitSettings

    settings = HospitalVisitSettings.get_settings()
    settings.last_deduction_check = current_time
    db.session.commit()

    return med_count, action_count
