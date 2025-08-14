"""add_scanner_system_tables

Revision ID: 88dcb87dd2aa
Revises: b40c722e5727
Create Date: 2025-08-14 13:46:26.551681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88dcb87dd2aa'
down_revision: Union[str, None] = 'b40c722e5727'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scanner system tables."""
    
    # 1. Add inventory_mode to medications table
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(medications)"))
    columns = [row[1] for row in result]
    
    if 'inventory_mode' not in columns:
        op.add_column('medications', 
            sa.Column('inventory_mode', sa.String(20), 
                     nullable=True,
                     server_default='legacy'))
    
    # 2. Create medication_packages table
    op.create_table('medication_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medication_id', sa.Integer(), nullable=False),
        sa.Column('package_size', sa.String(50), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('national_number', sa.String(50), nullable=True),
        sa.Column('national_number_type', sa.String(50), nullable=True),
        sa.Column('gtin', sa.String(14), nullable=True),
        sa.Column('country_code', sa.String(2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index('ix_medication_packages_gtin', 'medication_packages', ['gtin'])
    op.create_index('ix_medication_packages_national_number', 'medication_packages', ['national_number'])
    
    # 3. Create scanned_items table
    op.create_table('scanned_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medication_package_id', sa.Integer(), nullable=True),
        sa.Column('gtin', sa.String(14), nullable=True),
        sa.Column('national_number', sa.String(50), nullable=True),
        sa.Column('national_number_type', sa.String(50), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=False),
        sa.Column('batch_number', sa.String(50), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('scanned_by', sa.String(100), nullable=True),
        sa.Column('order_item_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('raw_data', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['medication_package_id'], ['medication_packages.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial_number', name='uq_scanned_items_serial')
    )
    
    # Create index for faster lookups
    op.create_index('ix_scanned_items_expiry_date', 'scanned_items', ['expiry_date'])
    op.create_index('ix_scanned_items_status', 'scanned_items', ['status'])
    
    # 4. Create package_inventory table
    op.create_table('package_inventory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medication_id', sa.Integer(), nullable=False),
        sa.Column('scanned_item_id', sa.Integer(), nullable=False),
        sa.Column('current_units', sa.Integer(), nullable=False),
        sa.Column('original_units', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='sealed'),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
        sa.ForeignKeyConstraint(['scanned_item_id'], ['scanned_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index('ix_package_inventory_status', 'package_inventory', ['status'])
    op.create_index('ix_package_inventory_medication_id', 'package_inventory', ['medication_id'])


def downgrade() -> None:
    """Remove scanner system tables."""
    
    # Drop tables in reverse order due to foreign keys
    op.drop_table('package_inventory')
    op.drop_table('scanned_items')
    op.drop_table('medication_packages')
    
    # Remove inventory_mode from medications
    # Note: SQLite doesn't support DROP COLUMN directly
    # This will only work if SQLite is compiled with ALTER TABLE DROP COLUMN support (3.35.0+)
    try:
        op.drop_column('medications', 'inventory_mode')
    except:
        pass  # Ignore if drop column is not supported