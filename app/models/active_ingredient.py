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
            "strength",
            "strength_unit",
            "form",
            name="uq_ingredient_name_strength_form",
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

    # Dosage strength (e.g., "100" for 100µg)
    strength: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Numeric strength value (e.g., 100, 500, 0.5)",
    )

    strength_unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Unit of strength (e.g., mg, µg, ml, IE)",
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

    def __repr__(self):
        strength_str = (
            f" {self.strength}{self.strength_unit}" if self.strength else ""
        )
        form_str = f" ({self.form})" if self.form else ""
        return f"<ActiveIngredient {self.name}{strength_str}{form_str}>"

    @property
    def full_name(self) -> str:
        """Get the full name including strength and form."""
        parts = [self.name]
        if self.strength and self.strength_unit:
            parts.append(f"{self.strength}{self.strength_unit}")
        if self.form:
            parts.append(f"({self.form})")
        return " ".join(parts)

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
