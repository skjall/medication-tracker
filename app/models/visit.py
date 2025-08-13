"""
This module defines physician visit and order related models.
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
    from .physician import Physician

# Create a logger for this module
logger = logging.getLogger(__name__)


class PhysicianVisit(db.Model):
    """
    Model representing a scheduled physician visit.
    Extended to support visit interval planning.
    """

    __tablename__ = "physician_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    physician_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("physicians.id"), nullable=True
    )
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # New field for tracking if an order should be for one or two visit intervals
    order_for_next_but_one: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="If true, orders for this visit should last until the next-but-one visit",
    )

    # Relationships
    physician: Mapped[Optional["Physician"]] = relationship(
        "Physician", back_populates="visits"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="physician_visit", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<PhysicianVisit {self.visit_date.strftime('%d.%m.%Y')}>"

    @property
    def days_until(self) -> int:
        """Calculate days until this physician visit."""
        return calculate_days_until(self.visit_date)


class Order(db.Model):
    """
    Model representing a medication order for a physician visit.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    physician_visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("physician_visits.id")
    )
    created_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Status can be 'planned', 'printed', 'fulfilled', 'partial'
    status: Mapped[str] = mapped_column(String(20), default="planned")

    # Relationships
    physician_visit: Mapped["PhysicianVisit"] = relationship(
        "PhysicianVisit", back_populates="orders"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    
    @property
    def fulfillment_summary(self) -> dict:
        """Get summary of fulfillment status for all items."""
        summary = {
            "total": len(self.order_items),
            "pending": 0,
            "fulfilled": 0,
            "modified": 0,
            "cancelled": 0
        }
        for item in self.order_items:
            if item.fulfillment_status in summary:
                summary[item.fulfillment_status] += 1
        return summary
    
    def update_status_from_items(self):
        """Update order status based on item fulfillment status."""
        summary = self.fulfillment_summary
        if summary["fulfilled"] == summary["total"] and summary["total"] > 0:
            self.status = "fulfilled"
        elif summary["fulfilled"] > 0 or summary["modified"] > 0:
            self.status = "partial"
        elif summary["cancelled"] == summary["total"] and summary["total"] > 0:
            self.status = "cancelled"
        # Keep current status if still planned/printed

    def __repr__(self) -> str:
        return f"<Order for visit {self.physician_visit_id}, status: {self.status}>"


class OrderItem(db.Model):
    """
    Model representing an item in a medication order.
    Now with individual fulfillment tracking.
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
    
    # Fulfillment tracking fields
    fulfillment_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, fulfilled, modified, cancelled
    fulfillment_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fulfilled_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="order_items"
    )
    
    @property
    def total_units_ordered(self) -> int:
        """Calculate total units from packages."""
        total = 0
        if self.medication:
            if self.medication.package_size_n1:
                total += self.packages_n1 * self.medication.package_size_n1
            if self.medication.package_size_n2:
                total += self.packages_n2 * self.medication.package_size_n2
            if self.medication.package_size_n3:
                total += self.packages_n3 * self.medication.package_size_n3
        return total

    def __repr__(self) -> str:
        med_name = self.medication.name if self.medication else "Unknown medication"
        return f"<OrderItem {med_name} for order {self.order_id} - {self.fulfillment_status}>"
