"""
Centralized timezone management for the Medication Tracker application.

This module provides a single source of truth for all timezone operations.
All timezone conversions in the application MUST go through this module.

Principles:
1. Database always stores UTC timestamps
2. User always sees local time (based on Settings.timezone)
3. Schedule times are interpreted as local time
4. All conversions are explicit and logged
"""

import logging
from datetime import datetime, time, date, timedelta
from typing import Optional, List, Tuple, Union
import pytz
from pytz import timezone as pytz_timezone

logger = logging.getLogger(__name__)


class TimezoneManager:
    """
    Central manager for all timezone operations.
    This is a singleton that ensures consistent timezone handling across the app.
    """
    
    _instance = None
    _user_timezone = None
    _timezone_string = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the timezone manager."""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._refresh_timezone()
    
    def _refresh_timezone(self):
        """Refresh the timezone from settings."""
        try:
            # Try to import and use Settings only if we're in an app context
            from flask import has_app_context
            
            if has_app_context():
                from models import Settings
                settings = Settings.get_settings()
                self._timezone_string = settings.timezone
                self._user_timezone = pytz_timezone(self._timezone_string)
                logger.info(f"Timezone set to: {self._timezone_string}")
            else:
                # Not in app context, use default
                if self._timezone_string is None:
                    self._timezone_string = "Europe/Berlin"
                    self._user_timezone = pytz_timezone("Europe/Berlin")
                    logger.debug("No app context, using default timezone: Europe/Berlin")
        except Exception as e:
            logger.error(f"Failed to load timezone from settings: {e}")
            # Fallback to Berlin time as default
            self._timezone_string = "Europe/Berlin"
            self._user_timezone = pytz_timezone("Europe/Berlin")
            logger.warning("Using fallback timezone: Europe/Berlin")
    
    @property
    def user_timezone(self):
        """Get the current user timezone."""
        if self._user_timezone is None:
            self._refresh_timezone()
        return self._user_timezone
    
    @property
    def timezone_string(self):
        """Get the current timezone as a string."""
        if self._timezone_string is None:
            self._refresh_timezone()
        return self._timezone_string
    
    def refresh(self):
        """Force refresh timezone from settings."""
        self._refresh_timezone()
    
    # Core conversion methods
    
    def utc_to_local(self, dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert a UTC datetime to local timezone.
        
        Args:
            dt: UTC datetime (must be timezone-aware or naive assumed UTC)
            
        Returns:
            Datetime in local timezone or None if input is None
        """
        if dt is None:
            return None
        
        # Ensure the datetime is timezone-aware in UTC
        if dt.tzinfo is None:
            # Naive datetime assumed to be UTC
            dt = pytz.UTC.localize(dt)
        elif dt.tzinfo != pytz.UTC:
            # Convert to UTC first if it's in another timezone
            dt = dt.astimezone(pytz.UTC)
        
        # Convert to local timezone
        local_dt = dt.astimezone(self.user_timezone)
        
        logger.debug(f"Converted UTC {dt.isoformat()} to local {local_dt.isoformat()}")
        return local_dt
    
    def local_to_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert a local datetime to UTC for storage.
        
        Args:
            dt: Local datetime (can be naive or aware)
            
        Returns:
            Datetime in UTC or None if input is None
        """
        if dt is None:
            return None
        
        # If naive, localize to user timezone
        if dt.tzinfo is None:
            # Naive datetime assumed to be in local timezone
            try:
                local_dt = self.user_timezone.localize(dt)
            except pytz.AmbiguousTimeError:
                # During DST fall-back, pick the first occurrence
                local_dt = self.user_timezone.localize(dt, is_dst=False)
            except pytz.NonExistentTimeError:
                # During DST spring-forward, this time doesn't exist
                # Move forward by 1 hour
                logger.warning(f"Non-existent time {dt} during DST transition, adjusting")
                adjusted_dt = dt + timedelta(hours=1)
                local_dt = self.user_timezone.localize(adjusted_dt)
        else:
            # Already timezone-aware, ensure it's in local timezone
            local_dt = dt.astimezone(self.user_timezone)
        
        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.UTC)
        
        logger.debug(f"Converted local {local_dt.isoformat()} to UTC {utc_dt.isoformat()}")
        return utc_dt
    
    def parse_schedule_time(self, time_str: str, for_date: date) -> datetime:
        """
        Parse a schedule time string (e.g., "08:00") for a specific date.
        Returns a timezone-aware datetime in LOCAL timezone.
        
        Args:
            time_str: Time in "HH:MM" format (interpreted as local time)
            for_date: The date to create the datetime for
            
        Returns:
            Timezone-aware datetime in local timezone
        """
        # Parse the time components
        try:
            hour, minute = map(int, time_str.split(':'))
        except (ValueError, AttributeError):
            logger.error(f"Invalid time format: {time_str}")
            raise ValueError(f"Invalid time format: {time_str}")
        
        # Create naive datetime
        naive_dt = datetime(
            for_date.year,
            for_date.month,
            for_date.day,
            hour,
            minute,
            0,
            0  # microseconds
        )
        
        # Localize to user timezone
        try:
            local_dt = self.user_timezone.localize(naive_dt)
        except pytz.AmbiguousTimeError:
            # During DST fall-back, pick the first occurrence
            local_dt = self.user_timezone.localize(naive_dt, is_dst=False)
            logger.warning(f"Ambiguous time {naive_dt} during DST, using is_dst=False")
        except pytz.NonExistentTimeError:
            # During DST spring-forward, this time doesn't exist
            logger.warning(f"Non-existent time {naive_dt} during DST transition")
            # Skip forward to the next valid time
            adjusted_dt = naive_dt + timedelta(hours=1)
            local_dt = self.user_timezone.localize(adjusted_dt)
        
        logger.debug(f"Parsed schedule time '{time_str}' on {for_date} as {local_dt.isoformat()}")
        return local_dt
    
    def parse_schedule_time_utc(self, time_str: str, for_date: date) -> datetime:
        """
        Parse a schedule time string and return it in UTC.
        
        Args:
            time_str: Time in "HH:MM" format (interpreted as local time)
            for_date: The date to create the datetime for
            
        Returns:
            Timezone-aware datetime in UTC
        """
        local_dt = self.parse_schedule_time(time_str, for_date)
        return local_dt.astimezone(pytz.UTC)
    
    def format_time_for_display(self, dt: Optional[datetime], format: str = "%H:%M") -> str:
        """
        Format a UTC datetime for display in local time.
        
        Args:
            dt: UTC datetime
            format: strftime format string
            
        Returns:
            Formatted string in local time or empty string if None
        """
        if dt is None:
            return ""
        
        local_dt = self.utc_to_local(dt)
        return local_dt.strftime(format)
    
    def format_datetime_for_display(self, dt: Optional[datetime], format: str = "%Y-%m-%d %H:%M") -> str:
        """
        Format a UTC datetime for display in local time with date.
        
        Args:
            dt: UTC datetime
            format: strftime format string
            
        Returns:
            Formatted string in local time or empty string if None
        """
        if dt is None:
            return ""
        
        local_dt = self.utc_to_local(dt)
        return local_dt.strftime(format)
    
    def get_local_now(self) -> datetime:
        """Get current time in local timezone."""
        return datetime.now(self.user_timezone)
    
    def get_utc_now(self) -> datetime:
        """Get current time in UTC."""
        return datetime.now(pytz.UTC)
    
    def get_today_local(self) -> date:
        """Get today's date in local timezone."""
        return self.get_local_now().date()
    
    def get_today_schedule_times(self, time_strings: List[str]) -> List[datetime]:
        """
        Get today's schedule times as timezone-aware datetimes in local timezone.
        
        Args:
            time_strings: List of time strings in "HH:MM" format
            
        Returns:
            List of timezone-aware datetimes for today in local timezone
        """
        today = self.get_today_local()
        return [self.parse_schedule_time(time_str, today) for time_str in time_strings]
    
    def is_time_in_past(self, time_str: str, for_date: date) -> bool:
        """
        Check if a scheduled time on a given date is in the past.
        
        Args:
            time_str: Time in "HH:MM" format
            for_date: The date to check
            
        Returns:
            True if the time is in the past
        """
        scheduled_time = self.parse_schedule_time(time_str, for_date)
        current_time = self.get_local_now()
        return scheduled_time <= current_time
    
    def calculate_next_dose_time(self, schedule_times: List[str], last_dose_utc: Optional[datetime] = None) -> Optional[datetime]:
        """
        Calculate the next dose time based on schedule times and last dose.
        
        Args:
            schedule_times: List of daily schedule times in "HH:MM" format
            last_dose_utc: Last dose time in UTC (optional)
            
        Returns:
            Next dose time in UTC, or None if no schedule times
        """
        if not schedule_times:
            return None
        
        current_local = self.get_local_now()
        today = current_local.date()
        
        # Get all times for today
        today_times = [self.parse_schedule_time(t, today) for t in schedule_times]
        
        # Find the next future time
        for scheduled_time in sorted(today_times):
            if scheduled_time > current_local:
                # If we have a last dose, make sure this is after it
                if last_dose_utc:
                    last_dose_local = self.utc_to_local(last_dose_utc)
                    if scheduled_time > last_dose_local:
                        return scheduled_time.astimezone(pytz.UTC)
                else:
                    return scheduled_time.astimezone(pytz.UTC)
        
        # No times left today, get first time tomorrow
        tomorrow = today + timedelta(days=1)
        tomorrow_first = self.parse_schedule_time(schedule_times[0], tomorrow)
        return tomorrow_first.astimezone(pytz.UTC)
    
    def validate_timezone(self, tz_string: str) -> bool:
        """
        Validate that a timezone string is valid.
        
        Args:
            tz_string: Timezone string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            pytz_timezone(tz_string)
            return True
        except pytz.UnknownTimeZoneError:
            return False
    
    def get_timezone_offset(self) -> str:
        """
        Get the current timezone offset string (e.g., "+02:00").
        
        Returns:
            Offset string
        """
        now = self.get_local_now()
        offset = now.strftime('%z')
        # Format as +HH:MM
        if offset:
            return f"{offset[:3]}:{offset[3:]}"
        return "+00:00"
    
    def get_timezone_abbr(self) -> str:
        """
        Get the current timezone abbreviation (e.g., "CEST").
        
        Returns:
            Timezone abbreviation
        """
        now = self.get_local_now()
        return now.strftime('%Z')


# Global singleton instance
timezone_manager = TimezoneManager()


# Convenience functions for backward compatibility and ease of use
def utc_to_local(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert UTC to local time."""
    return timezone_manager.utc_to_local(dt)


def local_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert local to UTC time."""
    return timezone_manager.local_to_utc(dt)


def parse_schedule_time(time_str: str, for_date: date) -> datetime:
    """Parse schedule time for a specific date."""
    return timezone_manager.parse_schedule_time(time_str, for_date)


def format_time_for_display(dt: Optional[datetime], format: str = "%H:%M") -> str:
    """Format time for display."""
    return timezone_manager.format_time_for_display(dt, format)


def format_datetime_for_display(dt: Optional[datetime], format: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime for display."""
    return timezone_manager.format_datetime_for_display(dt, format)


def get_local_now() -> datetime:
    """Get current local time."""
    return timezone_manager.get_local_now()


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return timezone_manager.get_utc_now()


def refresh_timezone():
    """Refresh timezone from settings."""
    timezone_manager.refresh()