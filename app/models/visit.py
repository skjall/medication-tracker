"""
This module defines hospital visit and order related models.
"""

# Standard library imports
from datetime import datetime
import logging
from typing import List, Optional, TYPE_CHECKING

# Third-party imports
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow
from utils import calculate_days_until

if TYPE_CHECKING:
    from .medication import Medication

# Create a logger for this module
logger = logging.getLogger(__name__)


class HospitalVisit(db.Model):
    """
    Model representing a scheduled hospital visit.
    Extended to support visit interval planning.
    """

    __tablename__ = "hospital_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # New field for tracking if an order should be for one or two visit intervals
    order_for_next_but_one: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="If true, orders for this visit should last until the next-but-one visit",
    )

    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="hospital_visit", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<HospitalVisit {self.visit_date.strftime('%d.%m.%Y')}>"

    @property
    def days_until(self) -> int:
        """Calculate days until this hospital visit."""
        return calculate_days_until(self.visit_date)


class Order(db.Model):
    """
    Model representing a medication order for a hospital visit.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hospital_visits.id")
    )
    created_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Status can be 'planned', 'printed', 'fulfilled'
    status: Mapped[str] = mapped_column(String(20), default="planned")

    # Relationships
    hospital_visit: Mapped["HospitalVisit"] = relationship(
        "HospitalVisit", back_populates="orders"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order for visit {self.hospital_visit_id}, status: {self.status}>"


class OrderItem(db.Model):
    """
    Model representing an item in a medication order.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    medication_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("medications.id"), nullable=True
    )

    quantity_needed: Mapped[int] = mapped_column(Integer)
    packages_n1: Mapped[int] = mapped_column(Integer, default=0)
    packages_n2: Mapped[int] = mapped_column(Integer, default=0)
    packages_n3: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="order_items"
    )

    def __repr__(self) -> str:
        med_name = self.medication.name if self.medication else "Unknown medication"
        return f"<OrderItem {med_name} for order {self.order_id}>"
