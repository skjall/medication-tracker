"""Add PDF template to physician

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2025-08-22 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i5j6k7l8m9n0'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade():
    # Add pdf_template_id column to physicians table
    with op.batch_alter_table('physicians', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pdf_template_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_physician_pdf_template', 'pdf_templates', ['pdf_template_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Remove pdf_template_id column from physicians table
    with op.batch_alter_table('physicians', schema=None) as batch_op:
        batch_op.drop_constraint('fk_physician_pdf_template', type_='foreignkey')
        batch_op.drop_column('pdf_template_id')