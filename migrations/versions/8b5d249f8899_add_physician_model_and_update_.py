"""Add physician model and update medication and visit relationships

Revision ID: 8b5d249f8899
Revises: d578b1d67a33
Create Date: 2025-06-03 22:17:23.932360

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b5d249f8899'
down_revision: Union[str, None] = 'd578b1d67a33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Get connection to check existing state
    conn = context.get_bind()

    # Check if physicians table exists
    physicians_exists = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='physicians'")).fetchone()

    if not physicians_exists:
        # Create physicians table if it doesn't exist
        op.create_table('physicians',
                        sa.Column('id', sa.Integer(), nullable=False),
                        sa.Column('name', sa.String(length=200), nullable=False),
                        sa.Column('specialty', sa.String(length=100), nullable=True),
                        sa.Column('phone', sa.String(length=50), nullable=True),
                        sa.Column('email', sa.String(length=200), nullable=True),
                        sa.Column('address', sa.Text(), nullable=True),
                        sa.Column('notes', sa.Text(), nullable=True),
                        sa.Column('created_at', sa.DateTime(), nullable=False),
                        sa.Column('updated_at', sa.DateTime(), nullable=False),
                        sa.PrimaryKeyConstraint('id')
                        )

    # Check if columns exist in medications table
    med_columns = conn.execute(sa.text("PRAGMA table_info(medications)")).fetchall()
    med_column_names = [col[1] for col in med_columns]

    # Update medications table using batch mode for SQLite compatibility - only if changes needed
    need_med_update = 'physician_id' not in med_column_names or 'is_otc' not in med_column_names
    if need_med_update:
        with op.batch_alter_table('medications', schema=None) as batch_op:
            if 'physician_id' not in med_column_names:
                batch_op.add_column(sa.Column('physician_id', sa.Integer(), nullable=True))
            if 'is_otc' not in med_column_names:
                batch_op.add_column(sa.Column('is_otc', sa.Boolean(), nullable=False, server_default='0', comment='True if medication is over-the-counter'))
            batch_op.create_foreign_key('fk_medications_physician_id', 'physicians', ['physician_id'], ['id'])

    # Check if physician_id column exists in physician_visits table
    visit_columns = conn.execute(sa.text("PRAGMA table_info(physician_visits)")).fetchall()
    visit_column_names = [col[1] for col in visit_columns]

    # Update physician_visits table using batch mode for SQLite compatibility - only if changes needed
    if 'physician_id' not in visit_column_names:
        with op.batch_alter_table('physician_visits', schema=None) as batch_op:
            batch_op.add_column(sa.Column('physician_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_physician_visits_physician_id', 'physicians', ['physician_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign keys and columns using batch mode for SQLite compatibility
    with op.batch_alter_table('physician_visits', schema=None) as batch_op:
        batch_op.drop_constraint('fk_physician_visits_physician_id', type_='foreignkey')
        batch_op.drop_column('physician_id')

    with op.batch_alter_table('medications', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medications_physician_id', type_='foreignkey')
        batch_op.drop_column('is_otc')
        batch_op.drop_column('physician_id')

    # Drop physicians table last
    op.drop_table('physicians')
