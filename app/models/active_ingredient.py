"""
Active ingredient (Wirkstoff) model for medication management.
This represents the actual pharmaceutical substance, independent of brand or manufacturer.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db, utcnow

if TYPE_CHECKING:
    from .medication_product import MedicationProduct
    from .schedule import MedicationSchedule
    from .visit import OrderItem
    from .ingredient_component import IngredientComponent


class ActiveIngredient(db.Model):
    """
    Represents an active pharmaceutical ingredient (Wirkstoff).
    This is the base level that allows medication substitution.

    Examples:
    - Salbutamol (regardless of manufacturer)
    - Ibuprofen (regardless of brand)
    - Metformin (regardless of formulation)
    """

    __tablename__ = "active_ingredients"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "form",
            name="uq_ingredient_name_form",
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize ingredient and set auto_deduction_enabled_at if needed."""
        super().__init__(**kwargs)
        
        # If auto_deduction is enabled on creation, set the enabled_at timestamp
        # This prevents retroactive deductions for periods before the ingredient was added
        if self.auto_deduction_enabled and self.auto_deduction_enabled_at is None:
            self.auto_deduction_enabled_at = utcnow()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic ingredient information
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Generic name of the active ingredient (e.g., Salbutamol)",
    )


    # Dosage form
    form: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Dosage form (e.g., tablet, capsule, inhalation, drops)",
    )

    # ATC code for classification
    atc_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="WHO ATC classification code"
    )

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Default product for this ingredient (preferred brand/manufacturer)
    default_product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("medication_products.id"),
        nullable=True,
        comment="Default product to prefer when multiple options exist"
    )
    
    # Auto-deduction settings
    auto_deduction_enabled: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        nullable=False,
        comment="Enable automatic inventory deduction for scheduled doses"
    )
    
    # Track when auto deduction was enabled to prevent retroactive deductions
    auto_deduction_enabled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True,
        comment="UTC timestamp when auto-deduction was last enabled"
    )
    
    # Inventory thresholds
    min_threshold: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        nullable=False,
        comment="Minimum inventory level before warning"
    )
    
    safety_margin_days: Mapped[int] = mapped_column(
        Integer, 
        default=30,
        nullable=False, 
        comment="Extra days to add when calculating needs"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    products: Mapped[list["MedicationProduct"]] = relationship(
        "MedicationProduct",
        back_populates="active_ingredient",
        cascade="all, delete-orphan",
        foreign_keys="MedicationProduct.active_ingredient_id"
    )
    
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="active_ingredient"
    )
    
    # Default product relationship
    default_product: Mapped[Optional["MedicationProduct"]] = relationship(
        "MedicationProduct",
        foreign_keys=[default_product_id],
        post_update=True  # Avoid circular dependency issues
    )
    
    # Medication schedules
    schedules: Mapped[list["MedicationSchedule"]] = relationship(
        "MedicationSchedule", 
        back_populates="active_ingredient", 
        cascade="all, delete-orphan"
    )
    
    # Ingredient components (for multi-component ingredients)
    components: Mapped[list["IngredientComponent"]] = relationship(
        "IngredientComponent",
        back_populates="active_ingredient",
        cascade="all, delete-orphan",
        order_by="IngredientComponent.sort_order"
    )

    def __repr__(self):
        form_str = f" ({self.form})" if self.form else ""
        return f"<ActiveIngredient {self.component_display}{form_str}>"

    @property
    def full_name(self) -> str:
        """Get the full name including components and form: Name (Component1 strength + Component2 strength, Form)."""
        if not self.components and not self.form:
            return self.name
        
        parts = []
        
        # Add component strengths if available
        if self.components:
            component_parts = []
            for comp in self.components:
                strength_float = float(comp.strength)
                if strength_float == int(strength_float):
                    strength_str = str(int(strength_float))
                else:
                    strength_str = f"{strength_float:g}"
                component_parts.append(f"{comp.component_name} {strength_str} {comp.strength_unit}")
            parts.append(" + ".join(component_parts))
        
        # Add form if available
        if self.form:
            parts.append(self.form)
        
        if parts:
            return f"{self.name} ({', '.join(parts)})"
        else:
            return self.name
    
    @property
    def clinical_name(self) -> str:
        """Get the clinical/generic name for orders and prescriptions."""
        return self.name
    
    @property
    def component_display(self) -> str:
        """Get formatted display showing all components with strengths (legacy method)."""
        if not self.components:
            return self.name
        
        return " + ".join([
            comp.display_text
            for comp in self.components
        ])
    
    @property
    def display_name(self) -> str:
        """Get the display name for UI: Name (components, form)."""
        return self.full_name

    def get_all_products(self):
        """Get all products containing this active ingredient."""
        return self.products

    def get_available_products(self):
        """Get all products that have inventory available."""
        # This will be implemented to check inventory across all products
        available = []
        for product in self.products:
            if product.total_inventory_count > 0:
                available.append(product)
        return available

    def find_substitutable_products(
        self, exclude_product_id: Optional[int] = None
    ):
        """
        Find products that can substitute for each other (aut_idem allowed).

        Args:
            exclude_product_id: Optional product ID to exclude from results

        Returns:
            List of substitutable products
        """
        substitutable = []
        for product in self.products:
            if product.id != exclude_product_id and product.aut_idem:
                substitutable.append(product)
        return substitutable
    
    @property
    def daily_usage(self) -> float:
        """Calculate daily usage based on schedules."""
        if not self.schedules:
            return 0.0
        return sum(schedule.calculate_daily_usage() for schedule in self.schedules)
    
    @property
    def total_inventory_count(self) -> float:
        """Get total inventory across all products."""
        total = 0
        for product in self.products:
            total += product.total_inventory_count
        return total
    
    @property
    def days_remaining(self) -> Optional[float]:
        """Calculate how many days of medication remain based on current inventory."""
        if self.daily_usage == 0:
            return None
        total_count = self.total_inventory_count
        if total_count == 0:
            return None
        return total_count / self.daily_usage
    
    @property
    def depletion_date(self) -> Optional[datetime]:
        """Calculate the date when medication will run out."""
        from datetime import timedelta
        if self.days_remaining is None:
            return None
        return utcnow() + timedelta(days=self.days_remaining)
    
    @property
    def is_low(self) -> bool:
        """Check if inventory is below minimum threshold."""
        return self.total_inventory_count < self.min_threshold
    
    @property
    def package_inventories(self):
        """Get all package inventories for this ingredient across all products."""
        from models import PackageInventory, ScannedItem, ProductPackage
        from sqlalchemy import or_
        
        all_packages = []
        
        # Collect package inventory for all products
        for product in self.products:
            # Get packages for this product
            packages = ProductPackage.query.filter_by(product_id=product.id).all()
            package_gtins = [p.gtin for p in packages if p.gtin]
            package_numbers = [(p.national_number, p.national_number_type) 
                              for p in packages if p.national_number]
            
            if package_gtins or package_numbers:
                # Build query for package inventory
                query = (
                    PackageInventory.query
                    .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
                    .filter(
                        PackageInventory.status.in_(['sealed', 'opened'])
                    )
                )
                
                # Build OR conditions
                conditions = []
                if package_gtins:
                    conditions.append(ScannedItem.gtin.in_(package_gtins))
                for nat_num, nat_type in package_numbers:
                    conditions.append(
                        (ScannedItem.national_number == nat_num) & 
                        (ScannedItem.national_number_type == nat_type)
                    )
                
                if conditions:
                    query = query.filter(or_(*conditions))
                    all_packages.extend(query.all())
        
        return all_packages
    
    def get_next_package_for_deduction(self):
        """Get the next package that would be used for deduction."""
        packages = self.package_inventories
        if not packages:
            return None
        
        # Sort by expiry date and return the one expiring soonest
        packages_with_expiry = []
        for pkg in packages:
            if pkg.current_units > 0:
                if pkg.scanned_item and pkg.scanned_item.expiry_date:
                    packages_with_expiry.append((pkg.scanned_item.expiry_date, pkg))
                else:
                    # No expiry date, add with far future date
                    from datetime import date
                    packages_with_expiry.append((date(9999, 12, 31), pkg))
        
        if packages_with_expiry:
            packages_with_expiry.sort(key=lambda x: x[0])
            return packages_with_expiry[0][1]
        
        return None
    
    @property
    def uses_package_system(self) -> bool:
        """Check if this ingredient uses the package-based inventory system."""
        return len(self.package_inventories) > 0
    
    @property
    def active_package_count(self) -> int:
        """Get count of active (non-empty) packages."""
        return len([p for p in self.package_inventories if p.current_units > 0])
    
    @property
    def is_otc(self) -> bool:
        """Check if this ingredient has any OTC products."""
        return any(product.is_otc for product in self.products)
    
    @property
    def aut_idem(self) -> bool:
        """Check if substitution is allowed for products with this ingredient."""
        # If any product forbids substitution, the ingredient should not allow it
        return all(product.aut_idem for product in self.products)
    
