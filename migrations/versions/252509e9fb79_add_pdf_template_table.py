"""add_pdf_template_table

Revision ID: 252509e9fb79
Revises: f85afb7f893c
Create Date: 2025-08-18 13:44:43.592547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '252509e9fb79'
down_revision: Union[str, None] = 'f85afb7f893c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pdf_templates table."""
    # Create pdf_templates table
    op.create_table('pdf_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Template name for user reference'),
        sa.Column('description', sa.Text(), nullable=True, comment='Description of what this template is for'),
        sa.Column('filename', sa.String(length=255), nullable=False, comment='Original PDF filename'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='Path to stored PDF file'),
        sa.Column('table_config', sa.JSON(), nullable=True, comment='Table detection configuration (rows, columns, boundaries)'),
        sa.Column('field_mappings', sa.JSON(), nullable=True, comment='Mapping of data fields to PDF form fields'),
        sa.Column('column_formulas', sa.JSON(), nullable=True, comment='Formulas for combining multiple fields in columns'),
        sa.Column('tab_order', sa.JSON(), nullable=True, comment='Ordered list of field names for tab navigation'),
        sa.Column('rows_per_page', sa.Integer(), nullable=False, server_default='20', comment='Number of rows in the table'),
        sa.Column('columns_count', sa.Integer(), nullable=False, server_default='5', comment='Number of columns in the table'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1', comment='Whether this template is available for use'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0', comment='Whether this is the default template'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop pdf_templates table."""
    op.drop_table('pdf_templates')
