"""
This module defines medication schedule models.
"""

# Standard library imports
from datetime import datetime
import enum
import json
import logging
from typing import List, Optional, TYPE_CHECKING

# Third-party imports
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow
from utils import ensure_timezone_utc

if TYPE_CHECKING:
    from .medication import Medication
    from .active_ingredient import ActiveIngredient

# Create a logger for this module
logger = logging.getLogger(__name__)


class ScheduleType(enum.Enum):
    """Enum for different types of medication schedules."""

    DAILY = "daily"
    INTERVAL = "interval"  # Every X days
    WEEKDAYS = "weekdays"  # Specific days of the week


class MedicationSchedule(db.Model):
    """
    Model representing a medication schedule with timing information.
    Multiple schedules can be defined for a single medication.
    """

    __tablename__ = "medication_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Legacy medication link (will be phased out)
    medication_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("medications.id"), nullable=True
    )
    
    # New active ingredient link (preferred)
    active_ingredient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("active_ingredients.id"), nullable=True
    )

    # Schedule type
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), nullable=False
    )

    # For interval type: take every X days (1 = daily, 2 = every other day, etc.)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)

    # For weekdays type: selected days (stored as JSON array of day numbers, 0=Monday, 6=Sunday)
    weekdays: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Time of day for taking medication (can be multiple)
    # Stored as JSON array of 24h format times, e.g., ["09:00", "17:00"]
    times_of_day: Mapped[str] = mapped_column(JSON, nullable=False)

    # Units to take at this schedule
    units_per_dose: Mapped[float] = mapped_column(Float, default=1.0)

    # Last automatic deduction date/time
    last_deduction: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    medication: Mapped[Optional["Medication"]] = relationship(
        "Medication", back_populates="schedules"
    )
    
    active_ingredient: Mapped[Optional["ActiveIngredient"]] = relationship(
        "ActiveIngredient", back_populates="schedules"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<MedicationSchedule {self.id} for medication {self.medication_id}>"

    @property
    def formatted_times(self) -> List[str]:
        """Return the list of times from the JSON string."""
        if isinstance(self.times_of_day, str):
            try:
                parsed = json.loads(self.times_of_day)
                if isinstance(parsed, list):
                    # Check if any individual time contains pipe separators (legacy data corruption)
                    result = []
                    for time_str in parsed:
                        if isinstance(time_str, str) and '|' in time_str:
                            # Split pipe-separated times
                            logger.warning(f"Pipe-separated time detected in schedule {self.id}: {time_str}")
                            result.extend(time_str.split('|'))
                        else:
                            result.append(time_str)
                    return result
                return parsed
            except json.JSONDecodeError:
                # Handle case where raw data contains pipes
                if '|' in self.times_of_day:
                    logger.warning(f"Raw pipe-separated times detected in schedule {self.id}: {self.times_of_day}")
                    return self.times_of_day.split('|')
                return [self.times_of_day]
        return self.times_of_day

    @property
    def formatted_weekdays(self) -> List[int]:
        """Return the list of weekdays from the JSON string."""
        if self.weekdays is None:
            return []
        if isinstance(self.weekdays, str):
            return json.loads(self.weekdays)
        return self.weekdays

    def is_due_now(self, current_time: datetime) -> bool:
        """
        Determine if a medication dose is due at the current time.

        Note: This method is used by the legacy auto-deduction system.
        For the enhanced system, see the deduction_service module which
        handles missed deductions more comprehensively.

        Args:
            current_time: The current datetime in UTC

        Returns:
            Boolean indicating if the medication is due
        """
        # Ensure current_time is timezone-aware UTC
        current_time = ensure_timezone_utc(current_time)

        # Convert to local timezone for comparison with schedule times
        from utils import to_local_timezone

        local_time = to_local_timezone(current_time)

        # Get current time in HH:MM format for comparison
        current_time_str = local_time.strftime("%H:%M")
        times_list = self.formatted_times

        # Check if current time matches any of the scheduled times (with 5-minute flexibility)
        # This allows for the scheduler running every hour to catch doses that might
        # otherwise be missed due to exact time matching
        time_match = False
        for scheduled_time in times_list:
            # Parse the scheduled time to compare with current time
            scheduled_hour, scheduled_minute = map(int, scheduled_time.split(":"))
            current_hour, current_minute = map(int, current_time_str.split(":"))

            # Calculate total minutes for both times
            scheduled_minutes = scheduled_hour * 60 + scheduled_minute
            current_minutes = current_hour * 60 + current_minute

            # Check if within 5 minutes of the scheduled time
            if abs(current_minutes - scheduled_minutes) <= 5:
                time_match = True
                break

        if not time_match:
            logger.debug(
                f"Current time {current_time_str} not within 5 minutes of any scheduled times {times_list}"
            )
            return False

        # If we've already deducted today, check if we should deduct again based on schedule
        if self.last_deduction is not None:
            last_deduction = ensure_timezone_utc(self.last_deduction)
            # Convert last deduction to local time for date comparison
            local_last_deduction = to_local_timezone(last_deduction)

            # For daily schedule, only deduct once per day per time slot
            if self.schedule_type == ScheduleType.DAILY:
                logger.debug(
                    f"This is a daily schedule. Last deduction was at {local_last_deduction.strftime('%H:%M')}"
                )
                # If last deduction was today and the same hour/minute (approximately), don't deduct again
                same_day = local_last_deduction.date() == local_time.date()

                # Check if the last deduction was for the same time slot (within 5 minutes)
                scheduled_hour, scheduled_minute = map(int, current_time_str.split(":"))
                last_hour, last_minute = map(
                    int, local_last_deduction.strftime("%H:%M").split(":")
                )

                scheduled_minutes = scheduled_hour * 60 + scheduled_minute
                last_minutes = last_hour * 60 + last_minute

                same_time_slot = abs(last_minutes - scheduled_minutes) <= 5

                if same_day and same_time_slot:
                    logger.debug(
                        f"Already deducted today at {local_last_deduction.strftime('%H:%M')}"
                    )
                    return False

            # For interval schedule, check if it's been interval_days since last deduction
            elif self.schedule_type == ScheduleType.INTERVAL:
                logger.debug(
                    f"This is an interval schedule. Last deduction was at {local_last_deduction.strftime('%d.%m.%Y')}"
                )
                days_since_last = (local_time.date() - local_last_deduction.date()).days
                # Only deduct if interval days have passed and we're at the right time
                if days_since_last < self.interval_days:
                    logger.debug(
                        f"Last deduction was only {days_since_last} days ago, not due yet"
                    )
                    return False

            # For weekday schedule, check if today is one of the selected days
            elif self.schedule_type == ScheduleType.WEEKDAYS:
                logger.debug(
                    f"This is a weekdays schedule. Last deduction was at {local_last_deduction.strftime('%d.%m.%Y')}"
                )
                # Get day of week (0=Monday, 6=Sunday) using local time
                current_weekday = local_time.weekday()
                # Check if it's the right day and we haven't already deducted at this time today
                if current_weekday not in self.formatted_weekdays:
                    return False

                # Check if we've already deducted today at this time slot
                same_day = local_last_deduction.date() == local_time.date()

                # Check if the last deduction was for the same time slot (within 5 minutes)
                scheduled_hour, scheduled_minute = map(int, current_time_str.split(":"))
                last_hour, last_minute = map(
                    int, local_last_deduction.strftime("%H:%M").split(":")
                )

                scheduled_minutes = scheduled_hour * 60 + scheduled_minute
                last_minutes = last_hour * 60 + last_minute

                same_time_slot = abs(last_minutes - scheduled_minutes) <= 5

                if same_day and same_time_slot:
                    logger.debug(
                        f"Already deducted today at {local_last_deduction.strftime('%H:%M')}"
                    )
                    return False

        # For daily schedule, it's due if the time matches and we haven't deducted yet today
        if self.schedule_type == ScheduleType.DAILY:
            logger.debug(
                f"This is a daily schedule. Current time {current_time_str} matches schedule"
            )
            return True

        # For interval schedule, we've already checked days since last deduction
        elif self.schedule_type == ScheduleType.INTERVAL:
            logger.debug(
                f"This is an interval schedule. Current time {current_time_str} matches schedule"
            )
            return True

        # For weekday schedule, we've already checked if today is one of the selected days
        elif self.schedule_type == ScheduleType.WEEKDAYS:
            logger.debug(
                f"This is a weekdays schedule. Current time {current_time_str} matches schedule"
            )
            # Get day of week (0=Monday, 6=Sunday) using local time
            current_weekday = local_time.weekday()
            return current_weekday in self.formatted_weekdays

        logger.debug(
            f"Schedule type {self.schedule_type} not recognized, cannot determine if due"
        )
        return False

    def calculate_daily_usage(self) -> float:
        """
        Calculate the average daily usage based on the schedule.
        Returns:
            Average daily usage in units
        """
        doses_per_day = len(self.formatted_times)

        if self.schedule_type == ScheduleType.DAILY:
            return doses_per_day * self.units_per_dose

        elif self.schedule_type == ScheduleType.INTERVAL:
            # For interval, divide by the interval days
            return (doses_per_day * self.units_per_dose) / self.interval_days

        elif self.schedule_type == ScheduleType.WEEKDAYS:
            # For weekdays, calculate based on number of days per week
            days_per_week = len(self.formatted_weekdays)
            return (doses_per_day * self.units_per_dose * days_per_week) / 7

        return 0.0
