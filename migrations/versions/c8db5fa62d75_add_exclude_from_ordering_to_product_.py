"""add exclude_from_ordering to product_packages

Revision ID: c8db5fa62d75
Revises: j6k7l8m9n0o1
Create Date: 2025-09-01 09:23:26.318258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8db5fa62d75'
down_revision: Union[str, None] = 'j6k7l8m9n0o1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add exclude_from_ordering column to product_packages table."""
    # Add exclude_from_ordering column with default value False
    with op.batch_alter_table('product_packages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('exclude_from_ordering', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove exclude_from_ordering column from product_packages table."""
    with op.batch_alter_table('product_packages', schema=None) as batch_op:
        batch_op.drop_column('exclude_from_ordering')