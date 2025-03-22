"""
Database models for the Medication Tracker application.

This module defines SQLAlchemy ORM models for:
- Medications
- Inventory
- Hospital visits
- Orders and order items
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, ForeignKey, func

db = SQLAlchemy()


class Medication(db.Model):
    """
    Model representing a medication with dosage information and package size options.
    """

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Number of times per day"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Package sizes
    package_size_n1: Mapped[int] = mapped_column(Integer, nullable=True)
    package_size_n2: Mapped[int] = mapped_column(Integer, nullable=True)
    package_size_n3: Mapped[int] = mapped_column(Integer, nullable=True)

    # Inventory management
    min_threshold: Mapped[int] = mapped_column(
        Integer, default=0, comment="Minimum inventory level before warning"
    )
    safety_margin_days: Mapped[int] = mapped_column(
        Integer, default=14, comment="Extra days to add when calculating needs"
    )

    # Relationships
    inventory: Mapped[Optional[Inventory]] = relationship(
        "Inventory", back_populates="medication", uselist=False
    )
    order_items: Mapped[List[OrderItem]] = relationship(
        "OrderItem", back_populates="medication"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<Medication {self.name}, {self.dosage} units, {self.frequency} times/day>"
        )

    @property
    def daily_usage(self) -> float:
        """Calculate daily usage based on dosage and frequency."""
        return self.dosage * self.frequency

    @property
    def days_remaining(self) -> Optional[float]:
        """Calculate how many days of medication remain based on current inventory."""
        if not self.inventory or self.daily_usage == 0:
            return None
        return self.inventory.current_count / self.daily_usage

    @property
    def depletion_date(self) -> Optional[datetime]:
        """Calculate the date when medication will run out."""
        if self.days_remaining is None:
            return None
        return datetime.utcnow() + timedelta(days=self.days_remaining)

    def calculate_needed_until_visit(
        self, visit_date: datetime, include_safety_margin: bool = True
    ) -> int:
        """
        Calculate how many units of medication are needed until the next hospital visit.

        Args:
            visit_date: The date of the next hospital visit
            include_safety_margin: Whether to include the safety margin days in the calculation

        Returns:
            The number of units needed
        """
        days_until_visit = (visit_date - datetime.utcnow()).days
        if days_until_visit < 0:
            days_until_visit = 0

        total_days = days_until_visit
        if include_safety_margin:
            total_days += self.safety_margin_days

        return int(total_days * self.daily_usage)

    def calculate_packages_needed(self, units_needed: int) -> Dict[str, int]:
        """
        Convert required units into package quantities, optimizing for package sizes.

        Args:
            units_needed: Total number of units/pills needed

        Returns:
            Dictionary with keys 'N1', 'N2', 'N3' and corresponding package counts
        """
        packages = {"N1": 0, "N2": 0, "N3": 0}
        remaining = units_needed

        # Try to use larger packages first if more efficient
        if self.package_size_n3 and self.package_size_n3 > 0:
            packages["N3"] = remaining // self.package_size_n3
            remaining %= self.package_size_n3

        if self.package_size_n2 and self.package_size_n2 > 0 and remaining > 0:
            packages["N2"] = remaining // self.package_size_n2
            remaining %= self.package_size_n2

        if self.package_size_n1 and self.package_size_n1 > 0 and remaining > 0:
            # Round up to ensure we have enough
            packages["N1"] = (
                remaining + self.package_size_n1 - 1
            ) // self.package_size_n1

        return packages


class Inventory(db.Model):
    """
    Model representing the current inventory for a medication.
    """

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medications.id"), unique=True
    )
    current_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="Current pill/unit count"
    )

    # Package counts
    packages_n1: Mapped[int] = mapped_column(Integer, default=0)
    packages_n2: Mapped[int] = mapped_column(Integer, default=0)
    packages_n3: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    medication: Mapped[Medication] = relationship(
        "Medication", back_populates="inventory"
    )
    inventory_logs: Mapped[List[InventoryLog]] = relationship(
        "InventoryLog", back_populates="inventory"
    )

    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Inventory for {self.medication.name}: {self.current_count} units>"

    @property
    def is_low(self) -> bool:
        """Check if the inventory is below the minimum threshold."""
        return self.current_count < self.medication.min_threshold

    def update_count(self, adjustment: int, notes: Optional[str] = None) -> None:
        """
        Update inventory count and create a log entry.

        Args:
            adjustment: The amount to adjust (positive for additions, negative for deductions)
            notes: Optional notes about the adjustment
        """
        previous_count = self.current_count
        self.current_count += adjustment
        self.last_updated = datetime.utcnow()

        # Create log entry
        log = InventoryLog(
            inventory_id=self.id,
            previous_count=previous_count,
            adjustment=adjustment,
            new_count=self.current_count,
            notes=notes,
        )
        db.session.add(log)

    def calculate_total_units_from_packages(self) -> int:
        """Calculate total units based on package counts and sizes."""
        total = 0
        if self.medication.package_size_n1:
            total += self.packages_n1 * self.medication.package_size_n1
        if self.medication.package_size_n2:
            total += self.packages_n2 * self.medication.package_size_n2
        if self.medication.package_size_n3:
            total += self.packages_n3 * self.medication.package_size_n3
        return total

    def update_from_packages(self) -> None:
        """Update current_count based on package quantities."""
        self.current_count = self.calculate_total_units_from_packages()
        self.last_updated = datetime.utcnow()


class InventoryLog(db.Model):
    """
    Model for tracking inventory changes.
    """

    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_id: Mapped[int] = mapped_column(Integer, ForeignKey("inventory.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    previous_count: Mapped[int] = mapped_column(Integer)
    adjustment: Mapped[int] = mapped_column(Integer)
    new_count: Mapped[int] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    inventory: Mapped[Inventory] = relationship(
        "Inventory", back_populates="inventory_logs"
    )

    def __repr__(self) -> str:
        change = "+" if self.adjustment > 0 else ""
        return f"<InventoryLog {self.timestamp}: {change}{self.adjustment}>"


class HospitalVisit(db.Model):
    """
    Model representing a scheduled hospital visit.
    """

    __tablename__ = "hospital_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    orders: Mapped[List[Order]] = relationship("Order", back_populates="hospital_visit")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<HospitalVisit {self.visit_date.strftime('%Y-%m-%d')}>"

    @property
    def days_until(self) -> int:
        """Calculate days until this hospital visit."""
        delta = self.visit_date - datetime.utcnow()
        return max(0, delta.days)


class Order(db.Model):
    """
    Model representing a medication order for a hospital visit.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hospital_visits.id")
    )
    created_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Status can be 'planned', 'printed', 'fulfilled'
    status: Mapped[str] = mapped_column(String(20), default="planned")

    # Relationships
    hospital_visit: Mapped[HospitalVisit] = relationship(
        "HospitalVisit", back_populates="orders"
    )
    order_items: Mapped[List[OrderItem]] = relationship(
        "OrderItem", back_populates="order"
    )

    def __repr__(self) -> str:
        return f"<Order for visit {self.hospital_visit_id}, status: {self.status}>"


class OrderItem(db.Model):
    """
    Model representing an item in a medication order.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"))
    medication_id: Mapped[int] = mapped_column(Integer, ForeignKey("medications.id"))

    quantity_needed: Mapped[int] = mapped_column(Integer)
    packages_n1: Mapped[int] = mapped_column(Integer, default=0)
    packages_n2: Mapped[int] = mapped_column(Integer, default=0)
    packages_n3: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="order_items")
    medication: Mapped[Medication] = relationship(
        "Medication", back_populates="order_items"
    )

    def __repr__(self) -> str:
        return f"<OrderItem {self.medication.name} for order {self.order_id}>"
