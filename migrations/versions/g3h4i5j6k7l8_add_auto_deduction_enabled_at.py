"""add auto_deduction_enabled_at to medications

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2025-08-20 07:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'g3h4i5j6k7l8'
down_revision = 'f2g3h4i5j6k7'
branch_labels = None
depends_on = None


def upgrade():
    # Add auto_deduction_enabled_at column to medications table
    with op.batch_alter_table('medications') as batch_op:
        batch_op.add_column(sa.Column('auto_deduction_enabled_at', sa.DateTime(), nullable=True, 
                                      comment='UTC timestamp when auto-deduction was last enabled'))
    
    # Set the enabled_at timestamp for medications that currently have auto-deduction enabled
    # We'll set it to now() for existing enabled medications to prevent retroactive deductions
    op.execute("""
        UPDATE medications 
        SET auto_deduction_enabled_at = CURRENT_TIMESTAMP
        WHERE auto_deduction_enabled = 1
    """)


def downgrade():
    # Remove auto_deduction_enabled_at column from medications table
    with op.batch_alter_table('medications') as batch_op:
        batch_op.drop_column('auto_deduction_enabled_at')