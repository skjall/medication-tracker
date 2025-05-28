"""Renamed hospital_visit to physician_visit

Revision ID: d578b1d67a33
Revises: 041b72841d80
Create Date: 2025-05-28 08:36:41.910851

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd578b1d67a33'
down_revision: Union[str, None] = '041b72841d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Disable foreign key constraints temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Create new orders table with physician_visit_id instead of hospital_visit_id
    op.execute('''
    CREATE TABLE orders_new (
        id INTEGER NOT NULL,
        physician_visit_id INTEGER NOT NULL,
        created_date DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(physician_visit_id) REFERENCES physician_visits (id)
    )
    ''')

    # Copy data from old table to new table, renaming the column in the process
    op.execute('''
    INSERT INTO orders_new (id, physician_visit_id, created_date, status)
    SELECT id, hospital_visit_id, created_date, status FROM orders
    ''')

    # Drop the old table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Re-enable foreign key constraints
    op.execute('PRAGMA foreign_keys = ON')


def downgrade() -> None:
    """Downgrade schema."""

    # Disable foreign key constraints temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Create orders table with the old column name
    op.execute('''
    CREATE TABLE orders_new (
        id INTEGER NOT NULL,
        hospital_visit_id INTEGER NOT NULL,
        created_date DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(hospital_visit_id) REFERENCES physician_visits (id)
    )
    ''')

    # Copy data back, renaming the column
    op.execute('''
    INSERT INTO orders_new (id, hospital_visit_id, created_date, status)
    SELECT id, physician_visit_id, created_date, status FROM orders
    ''')

    # Drop the current table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Re-enable foreign key constraints
    op.execute('PRAGMA foreign_keys = ON')