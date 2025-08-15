"""
Jinja template configuration module.
"""

from datetime import datetime, timezone
from flask_babel import gettext, ngettext
from models import Settings, utcnow
from utils import (
    min_value, 
    make_aware, 
    format_date, 
    format_datetime, 
    format_time, 
    to_local_timezone
)


def setup_jinja(app):
    """Configure Jinja2 template engine with custom filters and globals."""
    
    # Add utility functions to Jinja
    app.jinja_env.globals.update(min=min_value)
    app.jinja_env.globals.update(make_aware=make_aware)
    app.jinja_env.globals.update(format_date=format_date)
    app.jinja_env.globals.update(format_datetime=format_datetime)
    app.jinja_env.globals.update(format_time=format_time)
    app.jinja_env.globals.update(to_local_timezone=to_local_timezone)
    
    # Add translation functions to template globals
    app.jinja_env.globals['_'] = gettext
    app.jinja_env.globals['_n'] = ngettext

    # Context processor to add date/time variables to all templates
    @app.context_processor
    def inject_now():
        # Get UTC time first
        utc_now = utcnow()

        # Convert to local timezone
        local_now = to_local_timezone(utc_now)

        # Get settings for access in all templates
        settings = Settings.get_settings()

        # Return both UTC and local time, plus settings
        return {
            "now": local_now,  # Local time for display
            "utc_now": utc_now,  # UTC time for backend calculations
            "settings": settings,  # Application settings for templates
        }

    @app.template_filter("datetime")
    def parse_datetime(value):
        """Parse an ISO format datetime string into a datetime object."""
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            # If the string doesn't match ISO format, return current time as fallback
            return datetime.now(timezone.utc)