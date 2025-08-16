"""Add is_gs1 field to scanned_items table

Revision ID: c3e4254f5215
Revises: fcdedbcda84a
Create Date: 2025-01-17 00:30:00.000000

This migration adds a boolean field to track whether scanned item data
came from a GS1 DataMatrix scan (with batch/expiry) or a simple barcode.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'c3e4254f5215'
down_revision = 'fcdedbcda84a'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_gs1 field to scanned_items table."""
    
    # Check if column already exists (SQLite limitation workaround)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('scanned_items')]
    
    if 'is_gs1' not in columns:
        op.add_column('scanned_items', sa.Column('is_gs1', sa.Boolean(), nullable=False, server_default='0'))
        
        # Update existing records: If they have batch or expiry, they're likely GS1
        op.execute("""
            UPDATE scanned_items 
            SET is_gs1 = 1 
            WHERE batch_number IS NOT NULL OR expiry_date IS NOT NULL
        """)


def downgrade():
    """Remove is_gs1 field from scanned_items table."""
    
    # Check if column exists before dropping (SQLite limitation workaround)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('scanned_items')]
    
    if 'is_gs1' in columns:
        op.drop_column('scanned_items', 'is_gs1')