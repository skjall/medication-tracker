"""Remove old medication and inventory tables

Revision ID: a4a63fba526e
Revises: c8db5fa62d75
Create Date: 2025-09-01 20:35:43.310611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4a63fba526e'
down_revision: Union[str, None] = 'c8db5fa62d75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Remove old medication and inventory tables."""
    # Drop tables related to the old medication system if they exist
    # Note: These tables may already be dropped manually
    
    # Get table names to check what exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Drop tables if they exist
    if 'inventory_logs' in existing_tables:
        op.drop_table('inventory_logs')
    
    if 'inventory' in existing_tables:
        op.drop_table('inventory')
    
    if 'medications' in existing_tables:
        op.drop_table('medications')
    
    # For medication_schedules, we need to recreate the table without medication_id
    # because SQLite doesn't support dropping columns with foreign keys
    if 'medication_schedules' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('medication_schedules')]
        if 'medication_id' in columns:
            # Create a new table without medication_id
            op.create_table('medication_schedules_new',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('schedule_type', sa.String(length=8), nullable=False),
                sa.Column('interval_days', sa.Integer(), nullable=False),
                sa.Column('weekdays', sa.JSON(), nullable=True),
                sa.Column('times_of_day', sa.JSON(), nullable=False),
                sa.Column('units_per_dose', sa.Float(), nullable=False),
                sa.Column('last_deduction', sa.DateTime(), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=False),
                sa.Column('updated_at', sa.DateTime(), nullable=False),
                sa.Column('active_ingredient_id', sa.Integer(), nullable=True),
                sa.ForeignKeyConstraint(['active_ingredient_id'], ['active_ingredients.id'], ),
                sa.PrimaryKeyConstraint('id')
            )
            
            # Copy data from old table to new table (excluding medication_id)
            op.execute("""
                INSERT INTO medication_schedules_new 
                (id, schedule_type, interval_days, weekdays, times_of_day, 
                 units_per_dose, last_deduction, created_at, updated_at, active_ingredient_id)
                SELECT id, schedule_type, interval_days, weekdays, times_of_day, 
                       units_per_dose, last_deduction, created_at, updated_at, active_ingredient_id
                FROM medication_schedules
            """)
            
            # Drop the old table
            op.drop_table('medication_schedules')
            
            # Rename the new table to the original name
            op.rename_table('medication_schedules_new', 'medication_schedules')


def downgrade() -> None:
    """Downgrade schema - Not supported, old system is permanently removed."""
    raise NotImplementedError("Cannot restore old medication system. This migration is irreversible.")
