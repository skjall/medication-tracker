"""
This module defines the inventory-related database models.
"""

# Standard library imports
from datetime import datetime
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .medication import Medication

# Third-party imports
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow

# Create a logger for this module
logger = logging.getLogger(__name__)


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
    # Use string-based imports to avoid circular dependencies
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="inventory"
    )
    inventory_logs: Mapped[List["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="inventory", cascade="all, delete-orphan"
    )

    last_updated: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

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
        self.last_updated = utcnow()

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
        self.last_updated = utcnow()


class InventoryLog(db.Model):
    """
    Model for tracking inventory changes.
    """

    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_id: Mapped[int] = mapped_column(Integer, ForeignKey("inventory.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    previous_count: Mapped[int] = mapped_column(Integer)
    adjustment: Mapped[int] = mapped_column(Integer)
    new_count: Mapped[int] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    inventory: Mapped["Inventory"] = relationship(
        "Inventory", back_populates="inventory_logs"
    )

    def __repr__(self) -> str:
        change = "+" if self.adjustment > 0 else ""
        return f"<InventoryLog {self.timestamp}: {change}{self.adjustment}>"
