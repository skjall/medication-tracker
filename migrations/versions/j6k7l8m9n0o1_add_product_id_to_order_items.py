"""add product_id to order_items

Revision ID: j6k7l8m9n0o1
Revises: c56088389a03
Create Date: 2025-08-27 09:43:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "j6k7l8m9n0o1"
down_revision = "c56088389a03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add product_id to order_items table to track selected product."""

    # Add product_id column to order_items table
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(
            sa.Column("product_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_order_items_product",
            "medication_products",
            ["product_id"],
            ["id"],
        )


def downgrade() -> None:
    """Remove product_id from order_items table."""

    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_constraint("fk_order_items_product", type_="foreignkey")
        batch_op.drop_column("product_id")
