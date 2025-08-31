"""Add active ingredients and medication products tables

Revision ID: 954eb4fc8ce2
Revises: c3e4254f5215
Create Date: 2025-08-17 11:36:45.322010

This migration adds a new three-tier structure for medications:
1. ActiveIngredient - The pharmaceutical substance (e.g., Salbutamol)
2. MedicationProduct - Specific branded/generic product (e.g., Salbutamol 1A Pharma)
3. MedicationPackage - Specific package variant (existing, enhanced)

The migration preserves all existing data and creates a mapping from the old structure.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '954eb4fc8ce2'
down_revision: Union[str, None] = 'c3e4254f5215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add new tables without breaking existing structure."""
    
    # Create active_ingredients table
    op.create_table('active_ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Generic name of the active ingredient (e.g., Salbutamol)'),
        sa.Column('strength', sa.String(length=50), nullable=True, comment='Numeric strength value (e.g., 100, 500, 0.5)'),
        sa.Column('strength_unit', sa.String(length=20), nullable=True, comment='Unit of strength (e.g., mg, µg, ml, IE)'),
        sa.Column('form', sa.String(length=100), nullable=True, comment='Pharmaceutical form (e.g., Tablette, Kapsel, Inhalation, Tropfen)'),
        sa.Column('atc_code', sa.String(length=10), nullable=True, comment='WHO ATC classification code'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create medication_products table
    op.create_table('medication_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('active_ingredient_id', sa.Integer(), nullable=False, comment='Reference to the active ingredient'),
        sa.Column('brand_name', sa.String(length=200), nullable=False, comment="Commercial name (e.g., 'Salbutamol 1A Pharma', 'Ventolin')"),
        sa.Column('manufacturer', sa.String(length=100), nullable=True, comment='Manufacturer or pharmaceutical company'),
        sa.Column('pzn', sa.String(length=20), nullable=True, comment='Pharmazentralnummer (PZN) or other national drug code'),
        sa.Column('aut_idem', sa.Boolean(), nullable=True, comment='True if generic substitution is allowed by physician'),
        sa.Column('physician_id', sa.Integer(), nullable=True, comment='Prescribing physician if prescription-only'),
        sa.Column('is_otc', sa.Boolean(), nullable=True, comment='True if over-the-counter (no prescription needed)'),
        sa.Column('legacy_medication_id', sa.Integer(), nullable=True, comment='Reference to original medication record during migration'),
        sa.Column('package_size_n1', sa.Integer(), nullable=True, comment='Units in N1 package for this product'),
        sa.Column('package_size_n2', sa.Integer(), nullable=True, comment='Units in N2 package for this product'),
        sa.Column('package_size_n3', sa.Integer(), nullable=True, comment='Units in N3 package for this product'),
        sa.Column('min_threshold', sa.Integer(), nullable=True, comment='Minimum inventory level before warning'),
        sa.Column('safety_margin_days', sa.Integer(), nullable=True, comment='Extra days to add when calculating needs'),
        sa.Column('auto_deduction_enabled', sa.Boolean(), nullable=True, comment='Enable automatic inventory deduction'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['active_ingredient_id'], ['active_ingredients.id'], ),
        sa.ForeignKeyConstraint(['legacy_medication_id'], ['medications.id'], ),
        sa.ForeignKeyConstraint(['physician_id'], ['physicians.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pzn')
    )
    
    # Add product_id to medication_packages table (nullable for backward compatibility)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('medication_packages')]
    
    if 'product_id' not in columns:
        op.add_column('medication_packages', 
            sa.Column('product_id', sa.Integer(), nullable=True)
        )
        # Add foreign key constraint
        try:
            op.create_foreign_key(
                'fk_medication_packages_product_id', 
                'medication_packages', 
                'medication_products', 
                ['product_id'], 
                ['id']
            )
        except Exception:
            # SQLite doesn't support adding foreign keys to existing tables
            pass
    
    # Migrate existing medication data to new structure
    migrate_existing_medications()


def migrate_existing_medications():
    """
    Migrate existing medications to the new three-tier structure.
    This creates ActiveIngredient and MedicationProduct records for each existing Medication.
    Uses the full medication name as the active ingredient name for simplicity.
    """
    conn = op.get_bind()
    
    # Get all existing medications
    medications_result = conn.execute(text("""
        SELECT id, name, active_ingredient, form, aut_idem, physician_id, is_otc,
               package_size_n1, package_size_n2, package_size_n3,
               min_threshold, safety_margin_days, auto_deduction_enabled, notes,
               created_at, updated_at
        FROM medications
    """))
    
    medications = medications_result.fetchall()
    
    # Track created ingredients to avoid duplicates
    ingredient_map = {}
    
    for med in medications:
        # Extract strength from medication name if possible
        import re
        medication_name = med.name
        strength = None
        strength_unit = None
        
        # Try to extract strength pattern (number + unit)
        strength_pattern = r'(\d+(?:[.,]\d+)?)\s*(mg|µg|mcg|g|ml|IE|I\.E\.|%)'
        match = re.search(strength_pattern, medication_name, re.IGNORECASE)
        
        if match:
            strength = match.group(1).replace(',', '.')  # Normalize decimal separator
            strength_unit = match.group(2)
            # Normalize units
            if strength_unit.lower() in ['mcg', 'μg']:
                strength_unit = 'µg'
            elif strength_unit.lower() in ['i.e.', 'ie']:
                strength_unit = 'IE'
            
            # Remove strength from name for ingredient name
            ingredient_name = medication_name[:match.start()].strip()
            # Also remove trailing separators
            ingredient_name = ingredient_name.rstrip('-').strip()
            
            # If nothing left, use full name
            if not ingredient_name:
                ingredient_name = medication_name
        else:
            # Use full name if no strength found
            ingredient_name = medication_name
        
        # Create unique key including strength
        ingredient_key = f"{ingredient_name}_{strength}_{strength_unit}_{med.form}".lower() if med.form else f"{ingredient_name}_{strength}_{strength_unit}".lower()
        
        # Create or get active ingredient
        if ingredient_key not in ingredient_map:
            # Check if ingredient already exists
            existing = conn.execute(text("""
                SELECT id FROM active_ingredients 
                WHERE LOWER(name) = :name AND 
                      (strength = :strength OR (strength IS NULL AND :strength IS NULL)) AND
                      (strength_unit = :strength_unit OR (strength_unit IS NULL AND :strength_unit IS NULL)) AND
                      (form = :form OR (form IS NULL AND :form IS NULL))
            """), {
                "name": ingredient_name.lower(), 
                "strength": strength,
                "strength_unit": strength_unit,
                "form": med.form
            }).fetchone()
            
            if existing:
                ingredient_id = existing.id
            else:
                # Create new active ingredient with extracted or full name
                result = conn.execute(text("""
                    INSERT INTO active_ingredients (name, strength, strength_unit, form, notes, created_at, updated_at)
                    VALUES (:name, :strength, :strength_unit, :form, :notes, :created_at, :updated_at)
                """), {
                    "name": ingredient_name,
                    "strength": strength,
                    "strength_unit": strength_unit,
                    "form": med.form,
                    "notes": f"Migrated from medication: {med.name}",
                    "created_at": med.created_at,
                    "updated_at": med.updated_at
                })
                ingredient_id = result.lastrowid
            
            ingredient_map[ingredient_key] = ingredient_id
        else:
            ingredient_id = ingredient_map[ingredient_key]
        
        # Create medication product
        conn.execute(text("""
            INSERT INTO medication_products (
                active_ingredient_id, brand_name, manufacturer, aut_idem,
                physician_id, is_otc, legacy_medication_id,
                package_size_n1, package_size_n2, package_size_n3,
                min_threshold, safety_margin_days, auto_deduction_enabled,
                notes, created_at, updated_at
            ) VALUES (
                :ingredient_id, :brand_name, :manufacturer, :aut_idem,
                :physician_id, :is_otc, :legacy_medication_id,
                :n1, :n2, :n3, :min_threshold, :safety_margin, :auto_deduction,
                :notes, :created_at, :updated_at
            )
        """), {
            "ingredient_id": ingredient_id,
            "brand_name": med.name,
            "manufacturer": "Unknown",  # Can be updated by user later
            "aut_idem": med.aut_idem if med.aut_idem is not None else True,
            "physician_id": med.physician_id,
            "is_otc": med.is_otc if med.is_otc is not None else False,
            "legacy_medication_id": med.id,
            "n1": med.package_size_n1,
            "n2": med.package_size_n2,
            "n3": med.package_size_n3,
            "min_threshold": med.min_threshold if med.min_threshold is not None else 0,
            "safety_margin": med.safety_margin_days if med.safety_margin_days is not None else 30,
            "auto_deduction": med.auto_deduction_enabled if med.auto_deduction_enabled is not None else True,
            "notes": med.notes,
            "created_at": med.created_at,
            "updated_at": med.updated_at
        })



def downgrade() -> None:
    """Downgrade schema - Remove new tables and columns."""
    
    # Remove foreign key and column from medication_packages
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if product_id column exists before trying to drop it
    columns = [col['name'] for col in inspector.get_columns('medication_packages')]
    if 'product_id' in columns:
        # Try to drop foreign key (may not work on SQLite)
        try:
            op.drop_constraint('fk_medication_packages_product_id', 'medication_packages', type_='foreignkey')
        except Exception:
            pass
        op.drop_column('medication_packages', 'product_id')
    
    # Drop new tables
    op.drop_table('medication_products')
    op.drop_table('active_ingredients')