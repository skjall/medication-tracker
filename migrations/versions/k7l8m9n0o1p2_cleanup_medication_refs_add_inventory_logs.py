"""cleanup medication refs and add inventory logs

Revision ID: k7l8m9n0o1p2
Revises: a4a63fba526e
Create Date: 2025-09-03 12:19:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k7l8m9n0o1p2"
down_revision = "a4a63fba526e"
branch_labels = None
depends_on = None


def upgrade():
    # Check if inventory_logs table already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Only create inventory_logs table if it doesn't exist
    if 'inventory_logs' not in existing_tables:
        op.create_table(
            "inventory_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("package_inventory_id", sa.Integer(), nullable=False),
            sa.Column(
                "change_type",
                sa.String(length=50),
                nullable=False,
                comment="Type of change: onboarded, deducted, manual_adjustment, opened, consumed, expired",
            ),
            sa.Column("units_before", sa.Float(), nullable=False),
            sa.Column("units_after", sa.Float(), nullable=False),
            sa.Column("units_changed", sa.Float(), nullable=False),
            sa.Column("status_before", sa.String(length=20), nullable=True),
            sa.Column("status_after", sa.String(length=20), nullable=True),
            sa.Column(
                "reason",
                sa.String(length=200),
                nullable=True,
                comment="Reason for the change (e.g., Automatic deduction, Manual correction)",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("changed_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["package_inventory_id"], ["package_inventory.id"]
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade():
    # Check if inventory_logs table exists before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Only drop inventory_logs table if it exists
    if 'inventory_logs' in existing_tables:
        op.drop_table("inventory_logs")
