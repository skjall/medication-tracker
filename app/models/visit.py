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
    from .physician import Physician
    from .active_ingredient import ActiveIngredient
    from .scanner import PackageInventory
    from .medication_product import MedicationProduct

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
    active_ingredient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("active_ingredients.id"), nullable=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("medication_products.id"), nullable=True,
        comment="Selected product for this order item"
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
    
    # Track actual units received vs ordered
    units_received: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Actual units received through scanning"
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    active_ingredient: Mapped["ActiveIngredient"] = relationship(
        "ActiveIngredient", back_populates="order_items"
    )
    product: Mapped[Optional["MedicationProduct"]] = relationship(
        "MedicationProduct", 
        foreign_keys=[product_id],
        backref="order_items"
    )
    
    # Note: linked_packages relationship is defined via backref in PackageInventory model
    
    @property
    def total_units_ordered(self) -> int:
        """Calculate total units from packages - needs product info."""
        # For now return the quantity_needed since we don't have product package sizes here
        return self.quantity_needed
    
    @property
    def linked_package_count(self) -> int:
        """Count the number of packages linked to this order item."""
        if hasattr(self, 'linked_packages'):
            return len(self.linked_packages)
        return 0
    
    @property
    def units_from_linked_packages(self) -> int:
        """Calculate total units from linked packages."""
        total = 0
        if hasattr(self, 'linked_packages'):
            for package in self.linked_packages:
                if package.status in ['sealed', 'open']:
                    total += package.original_units
        return total
    
    @property
    def fulfillment_progress(self) -> str:
        """Get fulfillment progress as a string."""
        return f"{self.units_received}/{self.quantity_needed}"
    
    @property
    def is_fully_fulfilled(self) -> bool:
        """Check if order item is fully fulfilled."""
        return self.units_received >= self.quantity_needed
    
    @property
    def fulfillment_percentage(self) -> float:
        """Calculate fulfillment percentage."""
        if self.quantity_needed == 0:
            return 100.0
        return (self.units_received / self.quantity_needed) * 100
    
    def update_fulfillment_status(self):
        """Update fulfillment status based on received units."""
        if self.units_received >= self.quantity_needed:
            self.fulfillment_status = "fulfilled"
            self.fulfilled_at = datetime.utcnow()
        elif self.units_received > 0:
            self.fulfillment_status = "partial"
        else:
            self.fulfillment_status = "pending"

    def __repr__(self) -> str:
        ingredient_name = self.active_ingredient.name if self.active_ingredient else "Unknown ingredient"
        return f"<OrderItem {ingredient_name} for order {self.order_id} - {self.fulfillment_status}>"
