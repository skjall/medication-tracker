"""add pdf_structure to templates

Revision ID: e1f2g3h4i5j6
Revises: 252509e9fb79
Create Date: 2025-08-18 16:20:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import json

# revision identifiers, used by Alembic.
revision = "e1f2g3h4i5j6"
down_revision = "252509e9fb79"
branch_labels = None
depends_on = None


def upgrade():
    # Add pdf_structure column to pdf_templates table
    with op.batch_alter_table("pdf_templates") as batch_op:
        batch_op.add_column(
            sa.Column(
                "pdf_structure",
                sa.JSON(),
                nullable=True,
                comment="Structure mapping for existing PDF form fields (patient info, medication rows)",
            )
        )


def downgrade():
    # Remove pdf_structure column from pdf_templates table
    with op.batch_alter_table("pdf_templates") as batch_op:
        batch_op.drop_column("pdf_structure")
