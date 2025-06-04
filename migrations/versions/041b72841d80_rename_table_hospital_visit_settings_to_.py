"""Rename table hospital_visit_settings to physician_visit_settings
Revision ID: 041b72841d80
Revises: 339f7d43eac9
Create Date: 2025-04-29 17:30:25.868718
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '041b72841d80'
down_revision: Union[str, None] = '339f7d43eac9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Explicitly disable foreign key support temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Check for any tables with foreign keys to hospital_visit_settings
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    fk_tables = []

    for table in tables:
        foreign_keys = inspector.get_foreign_keys(table)
        for fk in foreign_keys:
            if fk['referred_table'] == 'hospital_visit_settings':
                fk_tables.append((table, fk))

    # Create the new table with the same structure
    op.create_table('physician_visit_settings',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('default_visit_interval', sa.Integer(), nullable=False),
                    sa.Column('auto_schedule_visits', sa.Boolean(), nullable=False),
                    sa.Column('default_order_for_next_but_one', sa.Boolean(), nullable=False),
                    sa.Column('timezone_name', sa.String(length=50), nullable=False),
                    sa.Column('last_deduction_check', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Force data transfer with explicit column names
    op.execute('''
    INSERT INTO physician_visit_settings (
        id, default_visit_interval, auto_schedule_visits, default_order_for_next_but_one,
        timezone_name, last_deduction_check, updated_at
    )
    SELECT
        id, default_visit_interval, auto_schedule_visits, default_order_for_next_but_one,
        timezone_name, last_deduction_check, updated_at
    FROM hospital_visit_settings;
    ''')

    # Handle any foreign key relationships
    for table, fk in fk_tables:
        # Update the foreign key values if needed
        op.execute(f'''
        UPDATE {table}
        SET {fk['constrained_columns'][0]} = (
            SELECT id FROM physician_visit_settings
            WHERE physician_visit_settings.id = {table}.{fk['constrained_columns'][0]}
        )
        ''')

    # Now drop the old table
    op.drop_table('hospital_visit_settings')

    # Turn foreign keys back on
    op.execute('PRAGMA foreign_keys = ON')


def downgrade() -> None:
    """Downgrade schema."""
    # Explicitly disable foreign key support temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Recreate the original hospital_visit_settings table
    op.create_table('hospital_visit_settings',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('default_visit_interval', sa.INTEGER(), nullable=False),
                    sa.Column('auto_schedule_visits', sa.BOOLEAN(), nullable=False),
                    sa.Column('default_order_for_next_but_one', sa.BOOLEAN(), nullable=False),
                    sa.Column('timezone_name', sa.VARCHAR(length=50), nullable=False),
                    sa.Column('last_deduction_check', sa.DATETIME(), nullable=True),
                    sa.Column('updated_at', sa.DATETIME(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Transfer data back to hospital_visit_settings
    op.execute('''
    INSERT INTO hospital_visit_settings (
        id, default_visit_interval, auto_schedule_visits, default_order_for_next_but_one,
        timezone_name, last_deduction_check, updated_at
    )
    SELECT
        id, default_visit_interval, auto_schedule_visits, default_order_for_next_but_one,
        timezone_name, last_deduction_check, updated_at
    FROM physician_visit_settings;
    ''')

    # Check if any tables have foreign keys pointing to physician_visit_settings
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    fk_tables = []

    for table in tables:
        foreign_keys = inspector.get_foreign_keys(table)
        for fk in foreign_keys:
            if fk['referred_table'] == 'physician_visit_settings':
                fk_tables.append((table, fk))

    # Update any foreign key relationships
    for table, fk in fk_tables:
        # Similar to how we handled the upgrade path
        op.execute(f'''
        UPDATE {table}
        SET {fk['constrained_columns'][0]} = (
            SELECT id FROM hospital_visit_settings
            WHERE hospital_visit_settings.id = {table}.{fk['constrained_columns'][0]}
        )
        ''')

    # Drop the new table
    op.drop_table('physician_visit_settings')

    # Turn foreign keys back on
    op.execute('PRAGMA foreign_keys = ON')