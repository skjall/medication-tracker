"""
Ingredient component model for handling multi-component active ingredients.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from .base import db, utcnow


class IngredientComponent(db.Model):
    """
    Represents a single component within an active ingredient.
    
    For single-ingredient medications (e.g., Salbutamol 100µg):
    - One component: Salbutamol, 100, µg, order=1
    
    For combination medications (e.g., Kaftrio - Ivacaftor/Tezacaftor/Elexacaftor):
    - Multiple components: 
      - Ivacaftor, 75, mg, order=1
      - Tezacaftor, 50, mg, order=2
      - Elexacaftor, 100, mg, order=3
    """
    __tablename__ = 'ingredient_components'

    id = Column(Integer, primary_key=True)
    active_ingredient_id = Column(Integer, ForeignKey('active_ingredients.id'), nullable=False)
    component_name = Column(String(255), nullable=False, comment='Name of the chemical component (e.g., Ivacaftor)')
    strength = Column(Numeric(10, 3), nullable=False, comment='Strength amount (e.g., 75)')
    strength_unit = Column(String(10), nullable=False, comment='Unit of strength (e.g., mg, µg)')
    sort_order = Column(Integer, nullable=False, default=1, comment='Order for display (1=first)')
    
    # Timestamps
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    active_ingredient = relationship("ActiveIngredient", back_populates="components")

    def __repr__(self):
        return f"<IngredientComponent {self.component_name} {self.strength} {self.strength_unit}>"

    @property
    def display_text(self):
        """Get formatted display text for this component."""
        # Convert to float first to ensure proper formatting
        strength_float = float(self.strength)
        
        # Format strength to remove unnecessary decimal places
        if strength_float == int(strength_float):
            strength_str = str(int(strength_float))
        else:
            strength_str = f"{strength_float:g}"  # Remove trailing zeros
        return f"{self.component_name} {strength_str} {self.strength_unit}"