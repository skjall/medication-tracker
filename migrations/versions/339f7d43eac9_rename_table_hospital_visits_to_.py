"""Rename table hospital_visits to physician_visits
Revision ID: 339f7d43eac9
Revises: d8942309667d
Create Date: 2025-04-29 11:35:51.417669
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '339f7d43eac9'
down_revision: Union[str, None] = 'd8942309667d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Explicitly disable foreign key support temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Get the actual constraint name first
    inspector = sa.inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys('orders')
    fk_name = None
    for fk in foreign_keys:
        if fk['referred_table'] == 'hospital_visits':
            fk_name = fk.get('name')
            break

    # Create the new table with exact same structure
    op.create_table('physician_visits',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('visit_date', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('order_for_next_but_one', sa.Boolean(), nullable=False,
                 comment='If true, orders for this visit should last until the next-but-one visit'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # Force data transfer with explicit column names
    op.execute('''
    INSERT INTO physician_visits (
        id, visit_date, notes, order_for_next_but_one,
        created_at, updated_at
    )
    SELECT
        id, visit_date, notes, order_for_next_but_one,
        created_at, updated_at
    FROM hospital_visits;
    ''')

    # Update foreign keys in orders table
    op.execute('''
    UPDATE orders
    SET hospital_visit_id = (
        SELECT id FROM physician_visits
        WHERE physician_visits.id = orders.hospital_visit_id
    );
    ''')

    # SQLite doesn't support dropping constraints directly, so we need to rebuild the table
    # Create a new orders table (temporarily) without the constraint
    op.execute('''
    CREATE TABLE orders_new (
        id INTEGER NOT NULL,
        hospital_visit_id INTEGER NOT NULL,
        created_date DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL,
        PRIMARY KEY (id)
    )
    ''')

    # Copy data to the new table
    op.execute('''
    INSERT INTO orders_new (id, hospital_visit_id, created_date, status)
    SELECT id, hospital_visit_id, created_date, status FROM orders
    ''')

    # Drop the old table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Add the new foreign key constraint
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

    # Copy data again
    op.execute('''
    INSERT INTO orders_new (id, hospital_visit_id, created_date, status)
    SELECT id, hospital_visit_id, created_date, status FROM orders
    ''')

    # Drop the intermediate table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Now we can safely drop the old table
    op.drop_table('hospital_visits')

    # Turn foreign keys back on
    op.execute('PRAGMA foreign_keys = ON')

def downgrade() -> None:
    """Downgrade schema."""
    # Explicitly disable foreign key support temporarily
    op.execute('PRAGMA foreign_keys = OFF')

    # Recreate the original hospital_visits table
    op.create_table('hospital_visits',
        sa.Column('id', sa.INTEGER(), nullable=False, primary_key=True),
        sa.Column('visit_date', sa.DATETIME(), nullable=False),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('order_for_next_but_one', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False)
    )

    # Transfer data back to hospital_visits
    op.execute('''
    INSERT INTO hospital_visits (
        id, visit_date, notes, order_for_next_but_one,
        created_at, updated_at
    )
    SELECT
        id, visit_date, notes, order_for_next_but_one,
        created_at, updated_at
    FROM physician_visits;
    ''')

    # Create a new orders table without the constraint
    op.execute('''
    CREATE TABLE orders_new (
        id INTEGER NOT NULL,
        hospital_visit_id INTEGER NOT NULL,
        created_date DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL,
        PRIMARY KEY (id)
    )
    ''')

    # Copy data to the new table
    op.execute('''
    INSERT INTO orders_new (id, hospital_visit_id, created_date, status)
    SELECT id, hospital_visit_id, created_date, status FROM orders
    ''')

    # Drop the old table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Add back the original foreign key constraint
    op.execute('''
    CREATE TABLE orders_new (
        id INTEGER NOT NULL,
        hospital_visit_id INTEGER NOT NULL,
        created_date DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(hospital_visit_id) REFERENCES hospital_visits (id)
    )
    ''')

    # Copy data again
    op.execute('''
    INSERT INTO orders_new (id, hospital_visit_id, created_date, status)
    SELECT id, hospital_visit_id, created_date, status FROM orders
    ''')

    # Drop the intermediate table
    op.drop_table('orders')

    # Rename the new table to the original name
    op.rename_table('orders_new', 'orders')

    # Drop the new table
    op.drop_table('physician_visits')

    # Turn foreign keys back on
    op.execute('PRAGMA foreign_keys = ON')