"""make_medication_id_nullable_in_package_inventory

Revision ID: 1b901e45710c
Revises: i5j6k7l8m9n0
Create Date: 2025-08-26 19:47:05.998565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b901e45710c'
down_revision: Union[str, None] = 'i5j6k7l8m9n0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make medication_id nullable in package_inventory table."""
    # SQLite requires recreating the table to change constraints
    with op.batch_alter_table('package_inventory', recreate='always') as batch_op:
        batch_op.alter_column('medication_id',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade() -> None:
    """Revert medication_id to non-nullable in package_inventory table."""
    # Note: This will fail if there are NULL values in the column
    with op.batch_alter_table('package_inventory') as batch_op:
        batch_op.alter_column('medication_id',
                              existing_type=sa.Integer(),
                              nullable=False)
