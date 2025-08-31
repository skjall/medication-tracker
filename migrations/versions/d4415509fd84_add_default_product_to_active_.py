"""add_default_product_to_active_ingredients

Revision ID: d4415509fd84
Revises: d1e2f3g4h5i6
Create Date: 2025-08-17 20:11:26.591351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4415509fd84'
down_revision: Union[str, None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add default_product_id column to active_ingredients table
    with op.batch_alter_table('active_ingredients') as batch_op:
        batch_op.add_column(
            sa.Column(
                'default_product_id', 
                sa.Integer(), 
                nullable=True,
                comment='Default product to prefer when multiple options exist'
            )
        )
        batch_op.create_foreign_key(
            'fk_active_ingredients_default_product',
            'medication_products',
            ['default_product_id'],
            ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove default_product_id column from active_ingredients table
    with op.batch_alter_table('active_ingredients') as batch_op:
        batch_op.drop_constraint('fk_active_ingredients_default_product', type_='foreignkey')
        batch_op.drop_column('default_product_id')
