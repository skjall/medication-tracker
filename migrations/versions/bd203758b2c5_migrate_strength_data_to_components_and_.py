"""migrate strength data to components and remove old columns

Revision ID: bd203758b2c5
Revises: e93aca9d8f29
Create Date: 2025-09-05 10:51:49.256188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd203758b2c5'
down_revision: Union[str, None] = 'e93aca9d8f29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Migrate existing strength data to ingredient_components table
    connection = op.get_bind()
    
    # Get active ingredients with strength data
    result = connection.execute(sa.text("""
        SELECT id, name, strength, strength_unit 
        FROM active_ingredients 
        WHERE strength IS NOT NULL AND strength_unit IS NOT NULL
    """))
    
    # Insert component records for each active ingredient
    for row in result:
        ingredient_id, name, strength, strength_unit = row
        connection.execute(sa.text("""
            INSERT INTO ingredient_components (
                active_ingredient_id, component_name, strength, strength_unit, 
                sort_order, created_at, updated_at
            ) VALUES (
                :ingredient_id, :component_name, :strength, :strength_unit, 
                1, datetime('now'), datetime('now')
            )
        """), {
            'ingredient_id': ingredient_id,
            'component_name': name,  # Use the ingredient name as component name
            'strength': strength,
            'strength_unit': strength_unit
        })
    
    # Step 2: Remove strength and strength_unit columns by recreating table
    op.execute("""
        CREATE TABLE active_ingredients_new (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            form VARCHAR(100),
            atc_code VARCHAR(10),
            notes TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            default_product_id INTEGER,
            auto_deduction_enabled BOOLEAN,
            auto_deduction_enabled_at DATETIME,
            min_threshold INTEGER,
            safety_margin_days INTEGER,
            FOREIGN KEY (default_product_id) REFERENCES medication_products(id)
        )
    """)
    
    # Copy data excluding strength columns
    op.execute("""
        INSERT INTO active_ingredients_new (
            id, name, form, atc_code, notes, created_at, updated_at,
            default_product_id, auto_deduction_enabled, auto_deduction_enabled_at,
            min_threshold, safety_margin_days
        )
        SELECT 
            id, name, form, atc_code, notes, created_at, updated_at,
            default_product_id, auto_deduction_enabled, auto_deduction_enabled_at,
            min_threshold, safety_margin_days
        FROM active_ingredients
    """)
    
    op.drop_table('active_ingredients')
    op.execute("ALTER TABLE active_ingredients_new RENAME TO active_ingredients")


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Recreate active_ingredients table with strength columns
    op.execute("""
        CREATE TABLE active_ingredients_old (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            strength VARCHAR(50),
            strength_unit VARCHAR(20),
            form VARCHAR(100),
            atc_code VARCHAR(10),
            notes TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            default_product_id INTEGER,
            auto_deduction_enabled BOOLEAN,
            auto_deduction_enabled_at DATETIME,
            min_threshold INTEGER,
            safety_margin_days INTEGER,
            FOREIGN KEY (default_product_id) REFERENCES medication_products(id)
        )
    """)
    
    # Copy data back with strength data from components
    connection = op.get_bind()
    
    # First copy basic data
    op.execute("""
        INSERT INTO active_ingredients_old (
            id, name, form, atc_code, notes, created_at, updated_at,
            default_product_id, auto_deduction_enabled, auto_deduction_enabled_at,
            min_threshold, safety_margin_days
        )
        SELECT 
            id, name, form, atc_code, notes, created_at, updated_at,
            default_product_id, auto_deduction_enabled, auto_deduction_enabled_at,
            min_threshold, safety_margin_days
        FROM active_ingredients
    """)
    
    # Update strength data from components (only for single-component ingredients)
    result = connection.execute(sa.text("""
        SELECT ic.active_ingredient_id, ic.strength, ic.strength_unit
        FROM ingredient_components ic
        WHERE ic.sort_order = 1
    """))
    
    for row in result:
        ingredient_id, strength, strength_unit = row
        connection.execute(sa.text("""
            UPDATE active_ingredients_old 
            SET strength = :strength, strength_unit = :strength_unit
            WHERE id = :ingredient_id
        """), {
            'strength': strength,
            'strength_unit': strength_unit,
            'ingredient_id': ingredient_id
        })
    
    op.drop_table('active_ingredients')
    op.execute("ALTER TABLE active_ingredients_old RENAME TO active_ingredients")
    
    # Step 2: Remove component data (this will lose multi-component data)
    connection.execute(sa.text("DELETE FROM ingredient_components"))
