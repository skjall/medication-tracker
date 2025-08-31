"""
Jinja2 template filters for consistent timezone handling.

All filters assume UTC input and convert to local timezone for display.
"""

from datetime import datetime
from typing import Optional
from flask import current_app
from timezone_manager import timezone_manager


def register_filters(app):
    """Register all timezone-related filters with the Flask app."""
    
    @app.template_filter('localtime')
    def localtime_filter(dt: Optional[datetime], format: str = "%H:%M") -> str:
        """
        Convert UTC datetime to local time for display.
        
        Usage in template:
            {{ medication.last_deduction | localtime }}
            {{ medication.last_deduction | localtime("%Y-%m-%d %H:%M") }}
        """
        if dt is None:
            return ""
        
        local_dt = timezone_manager.utc_to_local(dt)
        return local_dt.strftime(format)
    
    @app.template_filter('localdate')
    def localdate_filter(dt: Optional[datetime], format: str = "%Y-%m-%d") -> str:
        """
        Convert UTC datetime to local date for display.
        
        Usage in template:
            {{ visit.scheduled_date | localdate }}
        """
        if dt is None:
            return ""
        
        local_dt = timezone_manager.utc_to_local(dt)
        return local_dt.strftime(format)
    
    @app.template_filter('localdatetime')
    def localdatetime_filter(dt: Optional[datetime], format: str = "%Y-%m-%d %H:%M") -> str:
        """
        Convert UTC datetime to local datetime for display.
        
        Usage in template:
            {{ inventory.last_updated | localdatetime }}
        """
        if dt is None:
            return ""
        
        local_dt = timezone_manager.utc_to_local(dt)
        return local_dt.strftime(format)
    
    @app.template_filter('relativetime')
    def relativetime_filter(dt: Optional[datetime]) -> str:
        """
        Show relative time (e.g., "2 hours ago", "in 3 days").
        
        Usage in template:
            {{ medication.last_deduction | relativetime }}
        """
        if dt is None:
            return "never"
        
        local_dt = timezone_manager.utc_to_local(dt)
        local_now = timezone_manager.get_local_now()
        
        delta = local_now - local_dt
        total_seconds = delta.total_seconds()
        
        if total_seconds < 0:
            # Future
            total_seconds = abs(total_seconds)
            prefix = "in "
            suffix = ""
        else:
            # Past
            prefix = ""
            suffix = " ago"
        
        if total_seconds < 60:
            return "just now" if suffix else "now"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            unit = "minute" if minutes == 1 else "minutes"
            return f"{prefix}{minutes} {unit}{suffix}"
        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            unit = "hour" if hours == 1 else "hours"
            return f"{prefix}{hours} {unit}{suffix}"
        elif total_seconds < 604800:
            days = int(total_seconds / 86400)
            unit = "day" if days == 1 else "days"
            return f"{prefix}{days} {unit}{suffix}"
        elif total_seconds < 2592000:
            weeks = int(total_seconds / 604800)
            unit = "week" if weeks == 1 else "weeks"
            return f"{prefix}{weeks} {unit}{suffix}"
        else:
            months = int(total_seconds / 2592000)
            unit = "month" if months == 1 else "months"
            return f"{prefix}{months} {unit}{suffix}"
    
    @app.template_filter('timezone_abbr')
    def timezone_abbr_filter(dummy=None) -> str:
        """
        Get current timezone abbreviation.
        
        Usage in template:
            {{ None | timezone_abbr }}  -> "CEST"
        """
        return timezone_manager.get_timezone_abbr()
    
    @app.template_filter('timezone_offset')
    def timezone_offset_filter(dummy=None) -> str:
        """
        Get current timezone offset.
        
        Usage in template:
            {{ None | timezone_offset }}  -> "+02:00"
        """
        return timezone_manager.get_timezone_offset()
    
    @app.template_filter('schedule_time')
    def schedule_time_filter(time_str: str) -> str:
        """
        Format a schedule time string for display.
        Adds timezone indicator if needed.
        
        Usage in template:
            {{ "08:00" | schedule_time }}  -> "08:00"
        """
        if not time_str:
            return ""
        return time_str  # Already in local time format
    
    @app.template_filter('next_dose_time')
    def next_dose_time_filter(schedule) -> str:
        """
        Calculate and display the next dose time for a schedule.
        
        Usage in template:
            {{ schedule | next_dose_time }}
        """
        if not schedule or not schedule.formatted_times:
            return "No schedule"
        
        next_dose_utc = timezone_manager.calculate_next_dose_time(
            schedule.formatted_times,
            schedule.last_deduction
        )
        
        if next_dose_utc:
            local_next = timezone_manager.utc_to_local(next_dose_utc)
            now = timezone_manager.get_local_now()
            
            # If it's today, just show time
            if local_next.date() == now.date():
                return f"Today at {local_next.strftime('%H:%M')}"
            # If it's tomorrow
            elif (local_next.date() - now.date()).days == 1:
                return f"Tomorrow at {local_next.strftime('%H:%M')}"
            else:
                return local_next.strftime("%Y-%m-%d %H:%M")
        
        return "No upcoming dose"
    
    app.logger.info("Timezone template filters registered")