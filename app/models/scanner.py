"""
Scanner-related database models for package tracking and barcode scanning.
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db, utcnow

if TYPE_CHECKING:
    from .medication import Medication
    from .visit import OrderItem


class MedicationPackage(db.Model):
    """
    Represents a specific package variant of a medication.
    Links to medication but includes package-specific data like PZN/GTIN.
    """
    
    __tablename__ = "medication_packages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_id: Mapped[int] = mapped_column(Integer, ForeignKey("medications.id"), nullable=False)
    
    # Package identification
    package_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # N1, N2, N3, or custom
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Number of units in package
    
    # National and international identifiers
    national_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # PZN, CIP13, CNK, etc.
    national_number_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # DE_PZN, FR_CIP13, etc.
    gtin: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)  # 14-digit GTIN
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # DE, FR, BE, etc.
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    
    # Relationships
    medication: Mapped["Medication"] = relationship("Medication", back_populates="packages")
    scanned_items: Mapped[list["ScannedItem"]] = relationship("ScannedItem", back_populates="package")
    
    def __repr__(self):
        return f"<MedicationPackage {self.medication.name if self.medication else 'Unknown'} {self.package_size}>"


class ScannedItem(db.Model):
    """
    Represents an individually scanned package with its unique serial number.
    Stores all DataMatrix information for full traceability.
    """
    
    __tablename__ = "scanned_items"
    __table_args__ = (
        UniqueConstraint('serial_number', name='uq_scanned_items_serial'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_package_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("medication_packages.id"), nullable=True
    )
    
    # Extracted data from DataMatrix
    gtin: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)
    national_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    national_number_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    
    # Scan metadata
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    scanned_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # User identifier
    
    # Optional links
    order_item_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("order_items.id"), nullable=True
    )
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), 
        default='active',
        nullable=False,
        comment="active, consumed, expired, returned"
    )
    
    # Raw data for future reference
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    package: Mapped[Optional["MedicationPackage"]] = relationship("MedicationPackage", back_populates="scanned_items")
    order_item: Mapped[Optional["OrderItem"]] = relationship("OrderItem", backref="scanned_items")
    package_inventory: Mapped[Optional["PackageInventory"]] = relationship(
        "PackageInventory", back_populates="scanned_item", uselist=False
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if the package is expired."""
        if not self.expiry_date:
            return False
        return datetime.now().date() > self.expiry_date
    
    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if not self.expiry_date:
            return None
        delta = self.expiry_date - datetime.now().date()
        return delta.days
    
    def __repr__(self):
        return f"<ScannedItem {self.serial_number} exp:{self.expiry_date}>"


class PackageInventory(db.Model):
    """
    Tracks the current state of scanned packages in inventory.
    Links scanned items to actual inventory management.
    """
    
    __tablename__ = "package_inventory"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_id: Mapped[int] = mapped_column(Integer, ForeignKey("medications.id"), nullable=False)
    scanned_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("scanned_items.id"), nullable=False)
    
    # Current state
    current_units: Mapped[int] = mapped_column(Integer, nullable=False)
    original_units: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default='sealed',
        nullable=False,
        comment="sealed, open, consumed, expired"
    )
    
    # Status timestamps
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    medication: Mapped["Medication"] = relationship("Medication", backref="package_inventories")
    scanned_item: Mapped["ScannedItem"] = relationship("ScannedItem", back_populates="package_inventory")
    
    @property
    def units_used(self) -> int:
        """Calculate how many units have been used from this package."""
        return self.original_units - self.current_units
    
    @property
    def percentage_remaining(self) -> float:
        """Calculate percentage of package remaining."""
        if self.original_units == 0:
            return 0.0
        return (self.current_units / self.original_units) * 100
    
    def open_package(self):
        """Mark package as opened."""
        if self.status == 'sealed':
            self.status = 'open'
            self.opened_at = utcnow()
    
    def consume_package(self):
        """Mark package as fully consumed."""
        self.status = 'consumed'
        self.consumed_at = utcnow()
        self.current_units = 0
    
    def __repr__(self):
        return f"<PackageInventory {self.status} {self.current_units}/{self.original_units}>"