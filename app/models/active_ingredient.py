"""
Active ingredient (Wirkstoff) model for medication management.
This represents the actual pharmaceutical substance, independent of brand or manufacturer.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db, utcnow

if TYPE_CHECKING:
    from .medication_product import MedicationProduct


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
