"""
This module defines the physician-related database models.
"""

# Standard library imports
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

# Third-party imports
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow

if TYPE_CHECKING:
    from .visit import PhysicianVisit
    from .pdf_template import PDFTemplate


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
    
    # PDF Template for orders
    pdf_template_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("pdf_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment="PDF template to use for this physician's orders"
    )

    # Relationships
    visits: Mapped[List["PhysicianVisit"]] = relationship(
        "PhysicianVisit", back_populates="physician", cascade="save-update"
    )
    pdf_template: Mapped[Optional["PDFTemplate"]] = relationship(
        "PDFTemplate", foreign_keys=[pdf_template_id]
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
