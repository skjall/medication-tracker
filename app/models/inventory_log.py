"""
Inventory logging model for tracking all inventory changes.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db, utcnow


class InventoryLog(db.Model):
    """
    Tracks all inventory changes for PackageInventory items.
    This replaces the old Inventory logging functionality.
    """
    
    __tablename__ = "inventory_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Link to package inventory
    package_inventory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("package_inventory.id"), nullable=False
    )
    
    # Change details
    change_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Type of change: onboarded, deducted, manual_adjustment, opened, consumed, expired"
    )
    
    # Unit changes
    units_before: Mapped[float] = mapped_column(Float, nullable=False)
    units_after: Mapped[float] = mapped_column(Float, nullable=False)
    units_changed: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Status changes
    status_before: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status_after: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Context and metadata
    reason: Mapped[Optional[str]] = mapped_column(
        String(200), 
        nullable=True,
        comment="Reason for the change (e.g., 'Automatic deduction', 'Manual correction')"
    )
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    
    # Relationships
    package_inventory: Mapped["PackageInventory"] = relationship(
        "PackageInventory", 
        backref="inventory_logs"
    )
    
    def __repr__(self):
        return f"<InventoryLog {self.change_type}: {self.units_changed} units>"
    
    @property
    def display_change_type(self) -> str:
        """Get human-readable change type."""
        change_types = {
            'onboarded': 'Onboarded',
            'deducted': 'Deducted',
            'manual_adjustment': 'Manual Adjustment',
            'opened': 'Package Opened',
            'consumed': 'Package Consumed',
            'expired': 'Package Expired',
        }
        return change_types.get(self.change_type, self.change_type.title())
    
    @property
    def units_display(self) -> str:
        """Get formatted unit change display."""
        if self.units_changed > 0:
            return f"+{self.units_changed}"
        else:
            return str(self.units_changed)