"""add_aut_idem_to_medication

Revision ID: b40c722e5727
Revises: 385e8421ca41
Create Date: 2025-08-14 12:25:39.546573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b40c722e5727'
down_revision: Union[str, None] = '385e8421ca41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists to make migration idempotent
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(medications)"))
    columns = [row[1] for row in result]
    
    if 'aut_idem' not in columns:
        # Add aut_idem column with default value of True (1 for SQLite)
        op.add_column('medications', 
            sa.Column('aut_idem', sa.Boolean(), 
                     nullable=False, 
                     server_default=sa.text('1'),
                     comment='True if generic substitution is allowed'))
    
    # Skip cosmetic ALTER COLUMN operations for SQLite


def downgrade() -> None:
    """Downgrade schema."""
    # Check if column exists before dropping
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(medications)"))
    columns = [row[1] for row in result]
    
    if 'aut_idem' in columns:
        # Note: SQLite doesn't support DROP COLUMN directly
        # This will only work if SQLite is compiled with ALTER TABLE DROP COLUMN support (3.35.0+)
        try:
            op.drop_column('medications', 'aut_idem')
        except:
            pass  # Ignore if drop column is not supported
