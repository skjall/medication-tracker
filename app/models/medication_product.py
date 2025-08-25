"""
Medication product model representing specific branded or generic products.
This is the middle tier between active ingredients and packages.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db, utcnow

if TYPE_CHECKING:
    from .active_ingredient import ActiveIngredient
    from .physician import Physician
    from .medication import Medication
    from .inventory import Inventory
    from .schedule import MedicationSchedule
    from .visit import OrderItem
    from .product_package import ProductPackage


class MedicationProduct(db.Model):
    """
    Represents a specific medication product from a manufacturer.
    This can be either a brand-name or generic product.
    
    Examples:
    - Salbutamol 1A Pharma 100µg
    - Salbutamol ratiopharm 100µg  
    - Ventolin (brand name for Salbutamol)
    """
    
    __tablename__ = "medication_products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Link to active ingredient
    active_ingredient_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("active_ingredients.id"), 
        nullable=False,
        comment="Reference to the active ingredient"
    )
    
    # Product identification
    brand_name: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Commercial name (e.g., 'Salbutamol 1A Pharma', 'Ventolin')"
    )
    
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Manufacturer or pharmaceutical company"
    )
    
    # Primary identifier - DEPRECATED (moved to ProductPackage)
    # Keep for backwards compatibility during migration
    pzn: Mapped[Optional[str]] = mapped_column(
        String(20), 
        nullable=True, 
        unique=True,
        comment="DEPRECATED - moved to ProductPackage. Kept for migration compatibility"
    )
    
    # Substitution control
    aut_idem: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        comment="True if generic substitution is allowed by physician"
    )
    
    # Physician and order info
    physician_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("physicians.id"), 
        nullable=True,
        comment="Prescribing physician for this medication"
    )
    
    is_otc: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="True if over-the-counter (no order needed)"
    )
    
    # Legacy reference for migration
    legacy_medication_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("medications.id"),
        nullable=True,
        comment="Reference to original medication record during migration"
    )
    
    # Package size definitions - DEPRECATED (moved to ProductPackage)
    # Keep for backwards compatibility during migration
    package_size_n1: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        comment="DEPRECATED - moved to ProductPackage. Kept for migration compatibility"
    )
    package_size_n2: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        comment="DEPRECATED - moved to ProductPackage. Kept for migration compatibility"
    )
    package_size_n3: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        comment="DEPRECATED - moved to ProductPackage. Kept for migration compatibility"
    )
    
    # Inventory management settings
    min_threshold: Mapped[int] = mapped_column(
        Integer, 
        default=0,
        comment="Minimum inventory level before warning"
    )
    safety_margin_days: Mapped[int] = mapped_column(
        Integer, 
        default=30,
        comment="Extra days to add when calculating needs"
    )
    auto_deduction_enabled: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        comment="Enable automatic inventory deduction"
    )
    
    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
    
    # Relationships
    active_ingredient: Mapped["ActiveIngredient"] = relationship(
        "ActiveIngredient", 
        back_populates="products",
        foreign_keys=[active_ingredient_id]
    )
    
    physician: Mapped[Optional["Physician"]] = relationship(
        "Physician", 
        backref="medication_products"
    )
    
    # Package relationship
    packages: Mapped[list["ProductPackage"]] = relationship(
        "ProductPackage",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    
    # Legacy medication relationship
    legacy_medication: Mapped[Optional["Medication"]] = relationship(
        "Medication",
        foreign_keys=[legacy_medication_id],
        backref="migrated_product"
    )
    
    def __repr__(self):
        return f"<MedicationProduct {self.brand_name} ({self.manufacturer})>"
    
    @property
    def display_name(self) -> str:
        """Get display name including manufacturer if available."""
        if self.manufacturer and self.manufacturer != "Unknown":
            return f"{self.brand_name} ({self.manufacturer})"
        return self.brand_name
    
    @property
    def can_substitute(self) -> bool:
        """Check if this product allows substitution."""
        return self.aut_idem
    
    @property
    def packages_as_dict(self) -> list:
        """Get packages as list of dictionaries for JSON serialization."""
        return [pkg.to_dict() for pkg in self.packages]
    
    def find_substitutes(self):
        """Find other products that can substitute for this one."""
        if not self.aut_idem:
            return []
        
        return self.active_ingredient.find_substitutable_products(
            exclude_product_id=self.id
        )
    
    @property
    def total_inventory_count(self) -> int:
        """
        Get total inventory count across all packages of this product.
        This includes both legacy inventory (if linked) and package inventory.
        """
        total = 0
        
        # If this product is linked to a legacy medication, include its inventory
        if self.legacy_medication:
            # Include legacy inventory count if exists
            if self.legacy_medication.inventory:
                total += self.legacy_medication.inventory.current_count
            
            # Add package inventory for the legacy medication
            from models import PackageInventory
            
            package_units = (
                db.session.query(db.func.sum(PackageInventory.current_units))
                .filter(
                    PackageInventory.medication_id == self.legacy_medication_id,
                    PackageInventory.status.in_(['sealed', 'open'])
                )
                .scalar()
            )
            
            if package_units:
                total += package_units
        
        # TODO: When ProductPackage inventory is implemented, add those packages here
        # Currently all inventory goes through legacy medication system
            
        return total
    
    @property
    def daily_usage(self) -> float:
        """
        Calculate daily usage based on schedules.
        During migration, this delegates to legacy medication if linked.
        """
        if self.legacy_medication:
            return self.legacy_medication.daily_usage
        
        # TODO: Implement direct schedule relationship for new products
        return 0.0
    
    def calculate_packages_needed(self, units_needed: int) -> dict[str, int]:
        """
        Calculate optimal package combination for required units.
        
        Args:
            units_needed: Total units required
            
        Returns:
            Dictionary with 'N1', 'N2', 'N3' package counts
        """
        packages = {"N1": 0, "N2": 0, "N3": 0}
        
        if units_needed <= 0:
            return packages
        
        # Build list of available package sizes
        available = []
        if self.package_size_n3:
            available.append(("N3", self.package_size_n3))
        if self.package_size_n2:
            available.append(("N2", self.package_size_n2))
        if self.package_size_n1:
            available.append(("N1", self.package_size_n1))
        
        if not available:
            return packages
        
        # Sort by size (largest first)
        available.sort(key=lambda x: x[1], reverse=True)
        
        # Find optimal package with minimum overage
        best_option = None
        min_overage = float('inf')
        
        for pkg_type, pkg_size in available:
            count = (units_needed + pkg_size - 1) // pkg_size  # Ceiling division
            overage = (count * pkg_size) - units_needed
            
            if overage < min_overage:
                min_overage = overage
                best_option = (pkg_type, count)
        
        if best_option:
            packages[best_option[0]] = best_option[1]
        
        return packages