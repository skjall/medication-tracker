# Standard library imports
from datetime import datetime, timezone
import logging

# Third-party imports
from flask_sqlalchemy import SQLAlchemy

# Create a logger for this module
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()


def utcnow() -> datetime:
    """Return timezone-aware current datetime in UTC."""
    return datetime.now(timezone.utc)
