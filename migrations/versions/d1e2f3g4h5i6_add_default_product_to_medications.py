"""Add default_product_id to medications for package ordering

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2025-08-17 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade():
    # Add default_product_id column to medications table
    with op.batch_alter_table('medications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_product_id', sa.Integer(), nullable=True, comment='Default product to use for ordering packages'))
        batch_op.create_foreign_key('fk_medications_default_product', 'medication_products', ['default_product_id'], ['id'])


def downgrade():
    # Remove default_product_id column from medications table
    with op.batch_alter_table('medications', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medications_default_product', type_='foreignkey')
        batch_op.drop_column('default_product_id')