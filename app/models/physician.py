"""
This module defines the physician-related database models.
"""

# Standard library imports
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

# Third-party imports
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow

if TYPE_CHECKING:
    from .medication import Medication
    from .visit import PhysicianVisit


class Physician(db.Model):
    """
    Model representing a physician/doctor who prescribes medications and schedules visits.
    """

    __tablename__ = "physicians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Contact information
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    medications: Mapped[List["Medication"]] = relationship(
        "Medication", back_populates="physician", cascade="save-update"
    )
    visits: Mapped[List["PhysicianVisit"]] = relationship(
        "PhysicianVisit", back_populates="physician", cascade="save-update"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<Physician {self.name}>"

    @property
    def display_name(self) -> str:
        """Return a formatted display name with specialty if available."""
        if self.specialty:
            return f"{self.name} ({self.specialty})"
        return self.name
