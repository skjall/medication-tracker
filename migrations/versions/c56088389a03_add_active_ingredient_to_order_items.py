"""add_active_ingredient_to_order_items

Revision ID: c56088389a03
Revises: 1b901e45710c
Create Date: 2025-08-27 00:06:52.676704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String


# revision identifiers, used by Alembic.
revision: str = 'c56088389a03'
down_revision: Union[str, None] = '1b901e45710c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add active_ingredient_id to order_items and migrate data from medication_id."""
    
    # First, add the new column
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.add_column(sa.Column('active_ingredient_id', sa.Integer(), nullable=True))
    
    # Migrate data from medication_id to active_ingredient_id
    # This requires looking up the active ingredient for each medication
    connection = op.get_bind()
    
    # Get all order items with medication_id
    result = connection.execute(
        sa.text("SELECT id, medication_id FROM order_items WHERE medication_id IS NOT NULL")
    )
    order_items = result.fetchall()
    
    for order_item in order_items:
        order_item_id = order_item[0]
        medication_id = order_item[1]
        
        # Look up the medication's active ingredient
        # First try to find via default product
        result = connection.execute(
            sa.text("""
                SELECT mp.active_ingredient_id 
                FROM medications m
                JOIN medication_products mp ON m.default_product_id = mp.id
                WHERE m.id = :med_id
            """),
            {"med_id": medication_id}
        )
        row = result.fetchone()
        
        if row and row[0]:
            active_ingredient_id = row[0]
        else:
            # Try to find via migrated product
            result = connection.execute(
                sa.text("""
                    SELECT mp.active_ingredient_id 
                    FROM medication_products mp
                    WHERE mp.legacy_medication_id = :med_id
                    LIMIT 1
                """),
                {"med_id": medication_id}
            )
            row = result.fetchone()
            if row and row[0]:
                active_ingredient_id = row[0]
            else:
                # Try to match by medication name
                result = connection.execute(
                    sa.text("""
                        SELECT ai.id 
                        FROM medications m
                        JOIN active_ingredients ai ON m.name = ai.name
                        WHERE m.id = :med_id
                        LIMIT 1
                    """),
                    {"med_id": medication_id}
                )
                row = result.fetchone()
                active_ingredient_id = row[0] if row else None
        
        # Update the order item with the active ingredient
        if active_ingredient_id:
            connection.execute(
                sa.text("""
                    UPDATE order_items 
                    SET active_ingredient_id = :ingredient_id 
                    WHERE id = :item_id
                """),
                {"ingredient_id": active_ingredient_id, "item_id": order_item_id}
            )
    
    # Now add the foreign key and drop the old column
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.create_foreign_key(
            'fk_order_items_active_ingredient_id', 
            'active_ingredients', 
            ['active_ingredient_id'], 
            ['id']
        )
        
        # Drop medication_id column and its constraint
        # SQLite doesn't support dropping constraints directly, but batch mode handles it
        batch_op.drop_column('medication_id')


def downgrade() -> None:
    """Re-add medication_id to order_items and migrate data back."""
    
    # Add medication_id column back
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.add_column(sa.Column('medication_id', sa.Integer(), nullable=True))
    
    # Migrate data back from active_ingredient_id to medication_id
    connection = op.get_bind()
    
    # Get all order items with active_ingredient_id
    result = connection.execute(
        sa.text("SELECT id, active_ingredient_id FROM order_items WHERE active_ingredient_id IS NOT NULL")
    )
    order_items = result.fetchall()
    
    for order_item in order_items:
        order_item_id = order_item[0]
        active_ingredient_id = order_item[1]
        
        # Find a medication for this active ingredient
        # First try via default product
        result = connection.execute(
            sa.text("""
                SELECT m.id 
                FROM medications m
                JOIN medication_products mp ON m.default_product_id = mp.id
                WHERE mp.active_ingredient_id = :ingredient_id
                LIMIT 1
            """),
            {"ingredient_id": active_ingredient_id}
        )
        row = result.fetchone()
        
        if row and row[0]:
            medication_id = row[0]
        else:
            # Try via legacy_medication_id
            result = connection.execute(
                sa.text("""
                    SELECT mp.legacy_medication_id 
                    FROM medication_products mp
                    WHERE mp.active_ingredient_id = :ingredient_id 
                    AND mp.legacy_medication_id IS NOT NULL
                    LIMIT 1
                """),
                {"ingredient_id": active_ingredient_id}
            )
            row = result.fetchone()
            if row and row[0]:
                medication_id = row[0]
            else:
                # Try by name match
                result = connection.execute(
                    sa.text("""
                        SELECT m.id 
                        FROM medications m
                        JOIN active_ingredients ai ON m.name = ai.name
                        WHERE ai.id = :ingredient_id
                        LIMIT 1
                    """),
                    {"ingredient_id": active_ingredient_id}
                )
                row = result.fetchone()
                medication_id = row[0] if row else None
        
        # Update the order item
        if medication_id:
            connection.execute(
                sa.text("""
                    UPDATE order_items 
                    SET medication_id = :med_id 
                    WHERE id = :item_id
                """),
                {"med_id": medication_id, "item_id": order_item_id}
            )
    
    # Add foreign key and drop active_ingredient_id
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.create_foreign_key(
            'order_items_medication_id_fkey',
            'medications',
            ['medication_id'],
            ['id']
        )
        
        # Drop active_ingredient_id
        batch_op.drop_column('active_ingredient_id')