"""add ingredient components table

Revision ID: e93aca9d8f29
Revises: k7l8m9n0o1p2
Create Date: 2025-09-05 10:34:50.729228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e93aca9d8f29'
down_revision: Union[str, None] = 'k7l8m9n0o1p2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, fix tables with foreign key constraints to deleted 'medications' table
    
    # 1. Recreate medication_packages table without medication_id foreign key
    op.execute("""
        CREATE TABLE IF NOT EXISTS medication_packages_new (
            id INTEGER PRIMARY KEY,
            package_size VARCHAR(50),
            quantity INTEGER,
            national_number VARCHAR(50),
            national_number_type VARCHAR(50),
            gtin VARCHAR(14),
            country_code VARCHAR(2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            product_id INTEGER,
            FOREIGN KEY (product_id) REFERENCES medication_products(id)
        )
    """)
    
    # Copy data excluding the problematic medication_id column
    op.execute("""
        INSERT INTO medication_packages_new (
            id, package_size, quantity, national_number, national_number_type, 
            gtin, country_code, created_at, updated_at, product_id
        )
        SELECT 
            id, package_size, quantity, national_number, national_number_type,
            gtin, country_code, created_at, updated_at, product_id
        FROM medication_packages
    """)
    
    op.drop_table('medication_packages')
    op.execute("ALTER TABLE medication_packages_new RENAME TO medication_packages")
    
    # 2. Recreate package_inventory table without medication_id foreign key
    op.execute("""
        CREATE TABLE IF NOT EXISTS package_inventory_new (
            id INTEGER PRIMARY KEY,
            scanned_item_id INTEGER NOT NULL,
            current_units INTEGER NOT NULL,
            original_units INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'sealed',
            opened_at DATETIME,
            consumed_at DATETIME,
            order_item_id INTEGER,
            FOREIGN KEY (scanned_item_id) REFERENCES scanned_items(id),
            FOREIGN KEY (order_item_id) REFERENCES order_items(id)
        )
    """)
    
    # Copy data excluding the problematic medication_id column
    op.execute("""
        INSERT INTO package_inventory_new (
            id, scanned_item_id, current_units, original_units,
            status, opened_at, consumed_at, order_item_id
        )
        SELECT 
            id, scanned_item_id, current_units, original_units,
            status, opened_at, consumed_at, order_item_id
        FROM package_inventory
    """)
    
    op.drop_table('package_inventory')
    op.execute("ALTER TABLE package_inventory_new RENAME TO package_inventory")
    
    # 3. Now create the ingredient_components table
    op.create_table(
        'ingredient_components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('active_ingredient_id', sa.Integer(), nullable=False),
        sa.Column('component_name', sa.String(length=255), nullable=False, comment='Name of the chemical component (e.g., Ivacaftor)'),
        sa.Column('strength', sa.Numeric(10, 3), nullable=False, comment='Strength amount (e.g., 75)'),
        sa.Column('strength_unit', sa.String(length=10), nullable=False, comment='Unit of strength (e.g., mg, µg)'),
        sa.Column('sort_order', sa.Integer(), nullable=False, comment='Order for display (1=first)', default=1),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['active_ingredient_id'], ['active_ingredients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop ingredient_components table
    op.drop_table('ingredient_components')
    
    # Restore original tables with medication_id foreign keys
    # Note: This downgrade assumes the medications table exists again
    
    # 1. Recreate package_inventory with medication_id foreign key
    op.execute("""
        CREATE TABLE package_inventory_old (
            id INTEGER PRIMARY KEY,
            medication_id INTEGER,
            scanned_item_id INTEGER NOT NULL,
            current_units INTEGER NOT NULL,
            original_units INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'sealed',
            opened_at DATETIME,
            consumed_at DATETIME,
            order_item_id INTEGER,
            FOREIGN KEY (scanned_item_id) REFERENCES scanned_items(id),
            FOREIGN KEY (medication_id) REFERENCES medications(id),
            FOREIGN KEY (order_item_id) REFERENCES order_items(id)
        )
    """)
    
    op.execute("""
        INSERT INTO package_inventory_old (
            id, scanned_item_id, current_units, original_units,
            status, opened_at, consumed_at, order_item_id
        )
        SELECT 
            id, scanned_item_id, current_units, original_units,
            status, opened_at, consumed_at, order_item_id
        FROM package_inventory
    """)
    
    op.drop_table('package_inventory')
    op.execute("ALTER TABLE package_inventory_old RENAME TO package_inventory")
    
    # 2. Recreate medication_packages with medication_id foreign key
    op.execute("""
        CREATE TABLE medication_packages_old (
            id INTEGER PRIMARY KEY,
            medication_id INTEGER NOT NULL,
            package_size VARCHAR(50),
            quantity INTEGER,
            national_number VARCHAR(50),
            national_number_type VARCHAR(50),
            gtin VARCHAR(14),
            country_code VARCHAR(2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            product_id INTEGER,
            FOREIGN KEY (medication_id) REFERENCES medications(id),
            FOREIGN KEY (product_id) REFERENCES medication_products(id)
        )
    """)
    
    op.execute("""
        INSERT INTO medication_packages_old (
            id, package_size, quantity, national_number, national_number_type,
            gtin, country_code, created_at, updated_at, product_id
        )
        SELECT 
            id, package_size, quantity, national_number, national_number_type,
            gtin, country_code, created_at, updated_at, product_id
        FROM medication_packages
    """)
    
    op.drop_table('medication_packages')
    op.execute("ALTER TABLE medication_packages_old RENAME TO medication_packages")
