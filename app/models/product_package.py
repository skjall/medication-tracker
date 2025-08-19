"""
Product package model for tracking different package configurations.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import db

if TYPE_CHECKING:
    from .medication_product import MedicationProduct


class ProductPackage(db.Model):
    """
    Represents a specific package configuration for a medication product.
    Each package has its own GTIN, national drug code, and quantity.
    
    Examples:
    - Ibuprofen 400mg N1 (20 tablets) with PZN 12345678
    - Ibuprofen 400mg N2 (50 tablets) with PZN 87654321
    - Ibuprofen 400mg N3 (100 tablets) with PZN 11223344
    """
    
    __tablename__ = "product_packages"
    __table_args__ = (
        UniqueConstraint('gtin', name='uq_product_packages_gtin'),
        UniqueConstraint('national_number', 'national_number_type', 
                        name='uq_product_packages_national'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("medication_products.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Package identification
    package_size: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        comment="N1, N2, N3, or custom size designation"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        comment="Number of units in this package"
    )
    
    # Unique identifiers
    gtin: Mapped[Optional[str]] = mapped_column(
        String(14), 
        nullable=True,
        comment="Global Trade Item Number (barcode)"
    )
    national_number: Mapped[Optional[str]] = mapped_column(
        String(20), 
        nullable=True,
        comment="National drug code (PZN, CIP13, CNK, etc.)"
    )
    national_number_type: Mapped[Optional[str]] = mapped_column(
        String(10), 
        nullable=True,
        comment="Type of national number (DE_PZN, FR_CIP13, BE_CNK, etc.)"
    )
    
    # Package details
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Package-specific manufacturer if different from product"
    )
    
    # Pricing (optional)
    list_price: Mapped[Optional[float]] = mapped_column(
        Float, 
        nullable=True,
        comment="Official list price for this package"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Integer, 
        default=1,
        nullable=False,
        comment="Whether this package is currently available"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    product: Mapped["MedicationProduct"] = relationship(
        "MedicationProduct", 
        back_populates="packages"
    )
    
    @property
    def display_name(self) -> str:
        """Get display name for the package."""
        return f"{self.product.brand_name} {self.package_size} ({self.quantity} units)"
    
    @property
    def identifier_display(self) -> str:
        """Get primary identifier for display."""
        if self.national_number:
            return f"{self.national_number_type or 'NDC'}: {self.national_number}"
        elif self.gtin:
            return f"GTIN: {self.gtin}"
        return "No identifier"
    
    def to_dict(self) -> dict:
        """Convert package to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'package_size': self.package_size,
            'quantity': self.quantity,
            'gtin': self.gtin,
            'national_number': self.national_number,
            'national_number_type': self.national_number_type,
            'manufacturer': self.manufacturer,
            'list_price': self.list_price
        }
    
    def __repr__(self):
        return f"<ProductPackage {self.product.brand_name} {self.package_size}>"