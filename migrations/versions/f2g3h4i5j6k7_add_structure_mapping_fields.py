"""add structure mapping fields to pdf_templates

Revision ID: f2g3h4i5j6k7
Revises: e1f2g3h4i5j6
Create Date: 2025-01-18 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f2g3h4i5j6k7'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade():
    # Add structure_mapping and mapping_step columns to pdf_templates table
    with op.batch_alter_table('pdf_templates') as batch_op:
        batch_op.add_column(sa.Column('structure_mapping', sa.JSON(), nullable=True, 
                                      comment='Maps PDF form fields to table grid positions (row, column)'))
        batch_op.add_column(sa.Column('mapping_step', sa.String(20), nullable=True, 
                                      default='structure',
                                      comment="Current mapping step: 'structure' or 'content'"))


def downgrade():
    # Remove columns from pdf_templates table
    with op.batch_alter_table('pdf_templates') as batch_op:
        batch_op.drop_column('structure_mapping')
        batch_op.drop_column('mapping_step')