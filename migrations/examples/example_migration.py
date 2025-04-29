"""Example migration showing how to add a column to an existing table.

Revision ID: example_revision
Revises:
Create Date: 2025-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'example_revision'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - adds a new column to medications table."""
    # Example: Add a new column to the medications table
    op.add_column('medications', sa.Column('external_id', sa.String(50), nullable=True))

    # Example: Create a new index
    op.create_index('idx_medications_external_id', 'medications', ['external_id'])

    # Example: Alter an existing column
    # op.alter_column('medications', 'dosage',
    #                 existing_type=sa.Float(),
    #                 type_=sa.Numeric(10, 2),
    #                 existing_nullable=False)

    # Example: Execute raw SQL
    # op.execute("UPDATE medications SET external_id = 'MED-' || id WHERE external_id IS NULL")


def downgrade() -> None:
    """Downgrade schema - removes the column."""
    # Example: Drop index first
    op.drop_index('idx_medications_external_id', table_name='medications')

    # Example: Drop column
    op.drop_column('medications', 'external_id')