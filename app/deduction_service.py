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
from datetime import datetime, timedelta
from typing import List, Tuple
import pytz

# Local application imports
from models import (
    ActiveIngredient,
    MedicationSchedule,
    ScheduleType,
    db,
    ensure_timezone_utc,
    utcnow,
)
# Use the new centralized timezone manager
from timezone_manager import (
    timezone_manager,
    utc_to_local,
    local_to_utc,
    parse_schedule_time
)

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
        List of tuples (schedule_id, entity_name, problematic_times)
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
                # Get entity name from active ingredient
                entity_name = "Unknown"
                if schedule.active_ingredient:
                    entity_name = schedule.active_ingredient.name
                elif schedule.medication:
                    entity_name = schedule.medication.name
                    
                problematic_schedules.append((schedule.id, entity_name, raw_times))
                logger.warning(f"Found pipe-separated times in schedule {schedule.id} for {entity_name}: {raw_times}")

            # Also check parsed data for pipe-separated individual entries
            try:
                times = schedule.formatted_times
                for time_str in times:
                    if isinstance(time_str, str) and '|' in time_str:
                        entity_name = "Unknown"
                        if schedule.active_ingredient:
                            entity_name = schedule.active_ingredient.name
                        elif schedule.medication:
                            entity_name = schedule.medication.name
                            
                        problematic_schedules.append((schedule.id, entity_name, str(times)))
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
    
    All returned times are in UTC for database storage.

    Args:
        schedule: The medication schedule to check
        current_time: Current datetime (will be converted to UTC if not already)

    Returns:
        List of datetime objects in UTC representing missed deductions
    """
    logger.debug(
        f"Calculating missed deductions for schedule {schedule.id} at {current_time.isoformat()}"
    )

    # Ensure current_time is in UTC
    if current_time.tzinfo is None:
        current_time = timezone_manager.local_to_utc(current_time)
    elif current_time.tzinfo != pytz.UTC:
        current_time = current_time.astimezone(pytz.UTC)

    # Get the last deduction time (in UTC) or use a fallback
    # IMPORTANT: Never go back before auto-deduction was enabled
    
    # First, check when auto-deduction was enabled
    auto_deduction_enabled_at = None
    if schedule.active_ingredient and schedule.active_ingredient.auto_deduction_enabled_at:
        auto_deduction_enabled_at = ensure_timezone_utc(schedule.active_ingredient.auto_deduction_enabled_at)
        logger.debug(f"Auto-deduction enabled at: {auto_deduction_enabled_at.isoformat()}")
    
    if schedule.last_deduction:
        logger.debug(
            f"Last deduction time found (UTC): {schedule.last_deduction.isoformat()}"
        )
        last_deduction_utc = ensure_timezone_utc(schedule.last_deduction)
        
        # If we have an enabled_at timestamp and last_deduction is before it,
        # use enabled_at instead to prevent retroactive deductions
        if auto_deduction_enabled_at and last_deduction_utc < auto_deduction_enabled_at:
            logger.debug(f"Last deduction is before auto-deduction was enabled, using enabled_at instead")
            last_deduction_utc = auto_deduction_enabled_at
    else:
        # If no deduction has been recorded yet, determine the starting point
        fallback_time = auto_deduction_enabled_at
        
        # If no enabled_at or it's None, use schedule creation time
        if fallback_time is None and schedule.created_at:
            fallback_time = ensure_timezone_utc(schedule.created_at)
            logger.debug(f"Using schedule creation time: {fallback_time.isoformat()}")
        
        # Final fallback: one day ago (but this should rarely happen)
        if fallback_time is None:
            fallback_time = current_time - timedelta(days=1)
            logger.debug(f"Using final fallback (1 day ago): {fallback_time.isoformat()}")
        
        last_deduction_utc = fallback_time
        logger.debug(f"No last deduction, using fallback: {last_deduction_utc.isoformat()}")

    # Convert to local times for schedule calculation
    local_current_time = utc_to_local(current_time)
    local_last_deduction = utc_to_local(last_deduction_utc)
    
    logger.info(
        f"  Time range analysis:"
    )
    logger.info(f"    Last deduction: {local_last_deduction.isoformat()} (local) / {last_deduction_utc.isoformat()} (UTC)")
    logger.info(f"    Current time:   {local_current_time.isoformat()} (local) / {current_time.isoformat()} (UTC)")
    logger.info(f"    Time difference: {(current_time - last_deduction_utc).total_seconds() / 3600:.1f} hours")

    # Get scheduled times in HH:MM format, with automatic pipe-separator fix
    scheduled_times = get_and_fix_scheduled_times(schedule)
    logger.info(f"    Scheduled times: {scheduled_times}")

    # Calculate missed deductions based on schedule type
    # These functions will return times in UTC
    missed_deductions_utc = []

    if str(schedule.schedule_type) == str(ScheduleType.DAILY):
        logger.debug("Calculating missed deductions for daily schedule")
        missed_deductions_utc = _calculate_daily_missed_deductions(
            schedule, last_deduction_utc, current_time, scheduled_times
        )

    elif str(schedule.schedule_type) == str(ScheduleType.INTERVAL):
        logger.debug("Calculating missed deductions for interval schedule")
        missed_deductions_utc = _calculate_interval_missed_deductions(
            schedule, last_deduction_utc, current_time, scheduled_times
        )

    elif str(schedule.schedule_type) == str(ScheduleType.WEEKDAYS):
        logger.debug("Calculating missed deductions for weekday schedule")
        missed_deductions_utc = _calculate_weekdays_missed_deductions(
            schedule, last_deduction_utc, current_time, scheduled_times
        )
    else:
        logger.warning(
            f"Unknown schedule type {schedule.schedule_type} for schedule {schedule.id}"
        )
        return []

    logger.info(f"    Result: Found {len(missed_deductions_utc)} missed deductions")

    if missed_deductions_utc:
        logger.info(f"    Missed deduction details:")
        for dt in missed_deductions_utc[:5]:  # Log first 5 only
            local_dt = utc_to_local(dt)
            logger.info(f"      - {local_dt.isoformat()} (local) / {dt.isoformat()} (UTC)")
        if len(missed_deductions_utc) > 5:
            logger.info(f"      ... and {len(missed_deductions_utc) - 5} more")
    else:
        logger.info(f"    No missed deductions - medication is up to date")

    return missed_deductions_utc


def _calculate_daily_missed_deductions(
    schedule: MedicationSchedule,
    last_deduction_utc: datetime,
    current_time_utc: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for daily schedules.
    
    IMPORTANT: This function now works entirely in UTC and returns UTC times.
    Schedule times are interpreted as local time and converted to UTC.

    Args:
        schedule: The medication schedule
        last_deduction_utc: Last deduction time in UTC
        current_time_utc: Current time in UTC
        scheduled_times: List of scheduled times in "HH:MM" format (local time)

    Returns:
        List of missed deduction times in UTC
    """
    missed_deductions_utc = []
    
    # Convert UTC times to local for date iteration
    local_last = utc_to_local(last_deduction_utc)
    local_current = utc_to_local(current_time_utc)
    
    # Start from the day after the last deduction
    # (we don't want to double-deduct for the same day)
    start_date = local_last.date()
    
    # If last deduction was before today's first scheduled time,
    # we might need to check today as well
    if scheduled_times:
        first_time_today = parse_schedule_time(scheduled_times[0], start_date)
        if local_last < first_time_today:
            # Last deduction was before first scheduled time today
            # So we should check from today
            pass
        else:
            # Last deduction was after or at first scheduled time
            # Start checking from tomorrow
            start_date = start_date + timedelta(days=1)
    
    end_date = local_current.date()
    
    logger.info(f"      Checking dates from {start_date} to {end_date}")
    
    # Iterate through each day
    current_date = start_date
    while current_date <= end_date:
        logger.info(f"      Checking date: {current_date}")
        
        for time_str in scheduled_times:
            # Parse the scheduled time for this date (returns local time)
            scheduled_local = parse_schedule_time(time_str, current_date)
            
            # Convert to UTC for comparison
            scheduled_utc = local_to_utc(scheduled_local)
            
            logger.info(f"        Time {time_str}: {scheduled_local} (local) -> {scheduled_utc} (UTC)")
            
            # Check if this scheduled time is:
            # 1. After the last deduction
            # 2. Before or at the current time
            if last_deduction_utc < scheduled_utc <= current_time_utc:
                missed_deductions_utc.append(scheduled_utc)
                logger.info(f"          -> MISSED DEDUCTION!")
            elif scheduled_utc <= last_deduction_utc:
                logger.info(f"          -> Already deducted")
            else:
                logger.info(f"          -> Future (not due yet)")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    return missed_deductions_utc


def _calculate_interval_missed_deductions(
    schedule: MedicationSchedule,
    last_deduction_utc: datetime,
    current_time_utc: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for interval schedules (every X days).
    
    Returns times in UTC.

    Args:
        schedule: The medication schedule
        last_deduction_utc: Last deduction time in UTC
        current_time_utc: Current time in UTC
        scheduled_times: List of scheduled times in "HH:MM" format (local time)

    Returns:
        List of missed deduction times in UTC
    """
    missed_deductions_utc = []
    interval_days = schedule.interval_days

    # Convert to local for date calculation
    local_last = utc_to_local(last_deduction_utc)
    local_current = utc_to_local(current_time_utc)

    # Calculate the first day in the interval after the last deduction
    last_deduction_date = local_last.date()
    current_date = local_current.date()

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
    for interval_date in interval_dates:
        for time_str in scheduled_times:
            # Parse the scheduled time for this date (returns local time)
            scheduled_local = parse_schedule_time(time_str, interval_date)
            
            # Convert to UTC
            scheduled_utc = local_to_utc(scheduled_local)

            # Only include times before current time
            if scheduled_utc <= current_time_utc:
                missed_deductions_utc.append(scheduled_utc)

    return missed_deductions_utc


def _calculate_weekdays_missed_deductions(
    schedule: MedicationSchedule,
    last_deduction_utc: datetime,
    current_time_utc: datetime,
    scheduled_times: List[str],
) -> List[datetime]:
    """
    Calculate missed deductions for weekday schedules.
    
    Returns times in UTC.

    Args:
        schedule: The medication schedule
        last_deduction_utc: Last deduction time in UTC
        current_time_utc: Current time in UTC
        scheduled_times: List of scheduled times in "HH:MM" format (local time)

    Returns:
        List of missed deduction times in UTC
    """
    missed_deductions_utc = []
    selected_weekdays = schedule.formatted_weekdays

    # Convert to local for date iteration
    local_last = utc_to_local(last_deduction_utc)
    local_current = utc_to_local(current_time_utc)

    # Get start and end dates
    start_date = local_last.date()
    
    # Start from the next day if we've already processed today
    if scheduled_times and local_last.time() >= datetime.strptime(scheduled_times[-1], "%H:%M").time():
        start_date = start_date + timedelta(days=1)
    
    end_date = local_current.date()

    # Iterate through each day from start to end
    current_date = start_date
    while current_date <= end_date:
        # Only process if this is a selected weekday
        if current_date.weekday() in selected_weekdays:
            for time_str in scheduled_times:
                # Parse the scheduled time for this date (returns local time)
                scheduled_local = parse_schedule_time(time_str, current_date)
                
                # Convert to UTC
                scheduled_utc = local_to_utc(scheduled_local)

                # Only include times that are:
                # 1. After the last deduction
                # 2. Before or at the current time
                if last_deduction_utc < scheduled_utc <= current_time_utc:
                    missed_deductions_utc.append(scheduled_utc)

        # Move to next day
        current_date += timedelta(days=1)

    return missed_deductions_utc


def perform_deductions(current_time: datetime = None) -> Tuple[int, int]:
    """
    Perform all pending deductions including missed ones.

    Args:
        current_time: Optional override for current time (for testing)

    Returns:
        Tuple of (number of ingredients deducted, number of deduction actions)
    """
    if current_time is None:
        current_time = utcnow()
    else:
        current_time = ensure_timezone_utc(current_time)

    # Convert to local time for logging
    local_current_time = utc_to_local(current_time)
    
    logger.info(f"=== DEDUCTION SERVICE STARTED ===")
    logger.info(f"Current time: {current_time.isoformat()} UTC / {local_current_time.isoformat()} Local")
    
    # Only process active ingredients
    ingredients = ActiveIngredient.query.filter_by(auto_deduction_enabled=True).all()

    logger.info(f"Found {len(ingredients)} active ingredients with auto-deduction enabled:")
    for ingredient in ingredients:
        logger.info(f"  - {ingredient.name} (enabled at: {ingredient.auto_deduction_enabled_at})")

    ingredient_count = 0  # Number of ingredients that had deductions
    action_count = 0  # Total number of deduction actions performed

    # REMOVED: Legacy medication processing - we only use ActiveIngredient now
    
    # Process active ingredients only
    for ingredient in ingredients:
        logger.info(f"\n--- Processing ingredient: {ingredient.name} ---")
        ingredient_deducted = False
        
        # Check each schedule for this ingredient
        for schedule in ingredient.schedules:
            logger.info(f"  Checking schedule {schedule.id} (type: {schedule.schedule_type})")
            logger.info(f"  Schedule times: {schedule.formatted_times}")
            
            # Log last deduction info
            if schedule.last_deduction:
                local_last_deduction = utc_to_local(ensure_timezone_utc(schedule.last_deduction))
                logger.info(f"  Last deduction: {schedule.last_deduction.isoformat()} UTC / {local_last_deduction.isoformat()} Local")
            else:
                logger.info(f"  Last deduction: None")
            
            # First, calculate any missed deductions
            missed_deductions = calculate_missed_deductions(schedule, current_time)

            # If we have missed deductions, apply them
            if missed_deductions:
                logger.info(
                    f"Applying {len(missed_deductions)} missed deductions for {ingredient.name}"
                )
                
                # Sort by timestamp to apply them in chronological order
                missed_deductions.sort()
                
                for deduction_time in missed_deductions:
                    # Deduct the scheduled amount from products
                    amount = schedule.units_per_dose
                    if amount > 0 and ingredient.total_inventory_count >= amount:
                        # Use the ingredient's method to get the next package for deduction
                        package_inventory = ingredient.get_next_package_for_deduction()
                        
                        if package_inventory and package_inventory.current_units >= amount:
                            # Deduct from the package inventory
                            old_status = package_inventory.status
                            package_inventory.current_units -= amount
                            
                            # Mark package as opened if it was sealed
                            if package_inventory.status == 'sealed':
                                package_inventory.open_package()
                                # Log the status change
                                package_inventory.log_status_change(
                                    old_status=old_status,
                                    new_status='opened',
                                    reason='Automatic deduction opened package'
                                )
                            
                            # Log the deduction
                            package_inventory.log_deduction(
                                units_deducted=amount,
                                reason=f"Automatic deduction for {ingredient.name}"
                            )
                            
                            # Mark package as consumed if fully used
                            if package_inventory.current_units <= 0:
                                package_inventory.status = 'consumed'
                                package_inventory.consumed_at = deduction_time
                            
                            deducted = True
                            action_count += 1
                            ingredient_deducted = True
                            
                            logger.info(
                                f"Deducted {amount} units from {ingredient.name} at {deduction_time.isoformat()}"
                            )
                        else:
                            deducted = False
                            logger.warning(
                                f"Could not find suitable package inventory for deduction of {amount} units from {ingredient.name}"
                            )
                    else:
                        logger.warning(
                            f"Not enough inventory to deduct {amount} units from {ingredient.name}. Current count: {ingredient.total_inventory_count}"
                        )
                
                # Update last deduction time to the most recent missed deduction
                if ingredient_deducted and missed_deductions:
                    schedule.last_deduction = missed_deductions[-1]
                    logger.debug(f"Updated last_deduction to {schedule.last_deduction.isoformat()} UTC")
            else:
                logger.info(
                    f"  No missed deductions found for {ingredient.name} on schedule {schedule.id}"
                )
        
        # Count the ingredient if any of its schedules had deductions
        if ingredient_deducted:
            ingredient_count += 1

    # Commit all changes
    if action_count > 0:
        db.session.commit()
        logger.info(f"=== DEDUCTION SERVICE COMPLETE ===")
        logger.info(f"Result: {action_count} deductions across {ingredient_count} ingredients")
    else:
        logger.info(f"=== DEDUCTION SERVICE COMPLETE ===")
        logger.info("Result: No deductions needed at this time")

    # Update the last deduction check time in settings
    from models import Settings

    settings = Settings.get_settings()
    settings.last_deduction_check = current_time
    db.session.commit()
    
    logger.info(f"Updated last_deduction_check to: {current_time.isoformat()}")

    return ingredient_count, action_count
