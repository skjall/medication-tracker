"""add product packages table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-17 15:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Create product_packages table
    op.create_table('product_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('package_size', sa.String(length=20), nullable=False, comment='N1, N2, N3, or custom size designation'),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='Number of units in this package'),
        sa.Column('gtin', sa.String(length=14), nullable=True, comment='Global Trade Item Number (barcode)'),
        sa.Column('national_number', sa.String(length=20), nullable=True, comment='National drug code (PZN, CIP13, CNK, etc.)'),
        sa.Column('national_number_type', sa.String(length=10), nullable=True, comment='Type of national number (DE_PZN, FR_CIP13, BE_CNK, etc.)'),
        sa.Column('manufacturer', sa.String(length=100), nullable=True, comment='Package-specific manufacturer if different from product'),
        sa.Column('list_price', sa.Float(), nullable=True, comment='Official list price for this package'),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1', comment='Whether this package is currently available'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['medication_products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gtin', name='uq_product_packages_gtin'),
        sa.UniqueConstraint('national_number', 'national_number_type', name='uq_product_packages_national')
    )
    
    # Create indexes for faster lookups
    op.create_index('ix_product_packages_product_id', 'product_packages', ['product_id'], unique=False)
    op.create_index('ix_product_packages_national_number', 'product_packages', ['national_number'], unique=False)
    op.create_index('ix_product_packages_gtin', 'product_packages', ['gtin'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_product_packages_gtin', table_name='product_packages')
    op.drop_index('ix_product_packages_national_number', table_name='product_packages')
    op.drop_index('ix_product_packages_product_id', table_name='product_packages')
    
    # Drop table
    op.drop_table('product_packages')