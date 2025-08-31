"""Add units_received to order_items for package substitution tracking

Revision ID: c1d2e3f4g5h6
Revises: a1b2c3d4e5f6
Create Date: 2025-08-17 16:51:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    # Add units_received column to order_items table
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('units_received', sa.Integer(), nullable=False, server_default='0', comment='Actual units received through scanning'))
    
    # Remove the server default after adding the column
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.alter_column('units_received', server_default=None)


def downgrade():
    # Remove units_received column from order_items table
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('units_received')