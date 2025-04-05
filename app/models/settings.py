"""
This module defines application settings models.
"""

# Standard library imports
from datetime import datetime
import logging
from typing import Optional

# Third-party imports
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# Local application imports
from .base import db, utcnow

# Create a logger for this module
logger = logging.getLogger(__name__)


class Settings(db.Model):
    """
    System-wide settings for hospital visits and planning.
    Singleton model (only one row expected).
    """

    __tablename__ = "hospital_visit_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Default interval between hospital visits in days (e.g., 90 days)
    default_visit_interval: Mapped[int] = mapped_column(Integer, default=90)

    # Whether to automatically create a visit at the default interval
    auto_schedule_visits: Mapped[bool] = mapped_column(Boolean, default=False)

    # Whether orders should by default cover until next-but-one visit
    default_order_for_next_but_one: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timezone setting for the application
    timezone_name: Mapped[str] = mapped_column(String(50), default="UTC")

    # Last automatic deduction check timestamp
    last_deduction_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<Settings interval={self.default_visit_interval} days>"

    @classmethod
    def get_settings(cls) -> "Settings":
        """
        Get or create the hospital visit settings.

        Returns:
            The settings object (singleton)
        """
        settings = cls.query.first()
        if settings is None:
            settings = cls(
                default_visit_interval=90,
                auto_schedule_visits=False,
                default_order_for_next_but_one=True,
                timezone_name="UTC",
            )
            db.session.add(settings)
            db.session.commit()
        return settings
