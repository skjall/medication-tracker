"""move auto_deduction to active_ingredient

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2025-08-20 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'h4i5j6k7l8m9'
down_revision = 'g3h4i5j6k7l8'
branch_labels = None
depends_on = None


def upgrade():
    # Add auto-deduction fields to active_ingredients table
    with op.batch_alter_table('active_ingredients') as batch_op:
        batch_op.add_column(sa.Column('auto_deduction_enabled', sa.Boolean(), nullable=True, 
                                      default=True, comment='Enable automatic inventory deduction for scheduled doses'))
        batch_op.add_column(sa.Column('auto_deduction_enabled_at', sa.DateTime(), nullable=True, 
                                      comment='UTC timestamp when auto-deduction was last enabled'))
        batch_op.add_column(sa.Column('min_threshold', sa.Integer(), nullable=True, 
                                      default=0, comment='Minimum inventory level before warning'))
        batch_op.add_column(sa.Column('safety_margin_days', sa.Integer(), nullable=True, 
                                      default=30, comment='Extra days to add when calculating needs'))
    
    # Set default values for new columns
    op.execute("""
        UPDATE active_ingredients 
        SET auto_deduction_enabled = 1,
            min_threshold = 0,
            safety_margin_days = 30
        WHERE auto_deduction_enabled IS NULL
    """)
    
    # Migrate data from medications to active_ingredients
    # First, find active ingredients that are linked to medications
    op.execute("""
        UPDATE active_ingredients
        SET auto_deduction_enabled = (
            SELECT m.auto_deduction_enabled
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE mp.active_ingredient_id = active_ingredients.id
            LIMIT 1
        ),
        auto_deduction_enabled_at = (
            SELECT m.auto_deduction_enabled_at
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE mp.active_ingredient_id = active_ingredients.id
            LIMIT 1
        ),
        min_threshold = (
            SELECT m.min_threshold
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE mp.active_ingredient_id = active_ingredients.id
            LIMIT 1
        ),
        safety_margin_days = (
            SELECT m.safety_margin_days
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE mp.active_ingredient_id = active_ingredients.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE mp.active_ingredient_id = active_ingredients.id
        )
    """)
    
    # Add active_ingredient_id to medication_schedules
    with op.batch_alter_table('medication_schedules') as batch_op:
        batch_op.add_column(sa.Column('active_ingredient_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_schedules_active_ingredient', 'active_ingredients', ['active_ingredient_id'], ['id'])
    
    # Migrate existing schedules from medication_id to active_ingredient_id
    op.execute("""
        UPDATE medication_schedules
        SET active_ingredient_id = (
            SELECT mp.active_ingredient_id
            FROM medication_products mp
            WHERE mp.legacy_medication_id = medication_schedules.medication_id
            LIMIT 1
        )
        WHERE medication_id IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM medication_products mp
            WHERE mp.legacy_medication_id = medication_schedules.medication_id
        )
    """)


def downgrade():
    # Remove active_ingredient_id from medication_schedules
    with op.batch_alter_table('medication_schedules') as batch_op:
        batch_op.drop_constraint('fk_schedules_active_ingredient', type_='foreignkey')
        batch_op.drop_column('active_ingredient_id')
    
    # Remove auto-deduction fields from active_ingredients table
    with op.batch_alter_table('active_ingredients') as batch_op:
        batch_op.drop_column('auto_deduction_enabled')
        batch_op.drop_column('auto_deduction_enabled_at')
        batch_op.drop_column('min_threshold')
        batch_op.drop_column('safety_margin_days')