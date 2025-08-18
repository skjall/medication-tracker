"""migrate_medication_packages_to_product_packages

Revision ID: f85afb7f893c
Revises: d4415509fd84
Create Date: 2025-08-18 08:53:30.973533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f85afb7f893c'
down_revision: Union[str, None] = 'd4415509fd84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate package sizes from medications to product_packages table."""
    
    # Get connection to execute raw SQL
    connection = op.get_bind()
    
    # First, get all medications that have been migrated to products
    medications_with_products = connection.execute(
        sa.text("""
            SELECT 
                m.id as medication_id,
                m.package_size_n1,
                m.package_size_n2,
                m.package_size_n3,
                mp.id as product_id,
                mp.pzn as legacy_pzn
            FROM medications m
            JOIN medication_products mp ON mp.legacy_medication_id = m.id
            WHERE m.package_size_n1 IS NOT NULL 
               OR m.package_size_n2 IS NOT NULL 
               OR m.package_size_n3 IS NOT NULL
        """)
    ).fetchall()
    
    # For each medication with package sizes, create ProductPackage entries
    for row in medications_with_products:
        medication_id = row[0]
        n1_size = row[1]
        n2_size = row[2]
        n3_size = row[3]
        product_id = row[4]
        legacy_pzn = row[5]
        
        # Create N1 package if exists
        if n1_size and n1_size > 0:
            # Check if package already exists
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N1'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity, 
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N1', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n1_size,
                        "pzn": f"{legacy_pzn}_N1" if legacy_pzn else None,
                        "pzn_type": "DE_PZN" if legacy_pzn else None
                    }
                )
        
        # Create N2 package if exists
        if n2_size and n2_size > 0:
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N2'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity,
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N2', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n2_size,
                        "pzn": f"{legacy_pzn}_N2" if legacy_pzn else None,
                        "pzn_type": "DE_PZN" if legacy_pzn else None
                    }
                )
        
        # Create N3 package if exists
        if n3_size and n3_size > 0:
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N3'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity,
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N3', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n3_size,
                        "pzn": f"{legacy_pzn}_N3" if legacy_pzn else None,
                        "pzn_type": "DE_PZN" if legacy_pzn else None
                    }
                )
    
    # Also migrate package sizes from medication_products that might have been set
    products_with_sizes = connection.execute(
        sa.text("""
            SELECT 
                id as product_id,
                package_size_n1,
                package_size_n2,
                package_size_n3,
                pzn
            FROM medication_products
            WHERE (package_size_n1 IS NOT NULL AND package_size_n1 > 0)
               OR (package_size_n2 IS NOT NULL AND package_size_n2 > 0)
               OR (package_size_n3 IS NOT NULL AND package_size_n3 > 0)
        """)
    ).fetchall()
    
    for row in products_with_sizes:
        product_id = row[0]
        n1_size = row[1]
        n2_size = row[2]
        n3_size = row[3]
        pzn = row[4]
        
        # Create N1 package if exists and not already created
        if n1_size and n1_size > 0:
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N1'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity,
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N1', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n1_size,
                        "pzn": f"{pzn}_N1" if pzn else None,
                        "pzn_type": "DE_PZN" if pzn else None
                    }
                )
        
        # Create N2 package if exists
        if n2_size and n2_size > 0:
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N2'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity,
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N2', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n2_size,
                        "pzn": f"{pzn}_N2" if pzn else None,
                        "pzn_type": "DE_PZN" if pzn else None
                    }
                )
        
        # Create N3 package if exists
        if n3_size and n3_size > 0:
            existing = connection.execute(
                sa.text("""
                    SELECT id FROM product_packages 
                    WHERE product_id = :product_id 
                    AND package_size = 'N3'
                """),
                {"product_id": product_id}
            ).fetchone()
            
            if not existing:
                connection.execute(
                    sa.text("""
                        INSERT INTO product_packages (
                            product_id, package_size, quantity,
                            national_number, national_number_type,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :product_id, 'N3', :quantity,
                            :pzn, :pzn_type,
                            1, datetime('now'), datetime('now')
                        )
                    """),
                    {
                        "product_id": product_id,
                        "quantity": n3_size,
                        "pzn": f"{pzn}_N3" if pzn else None,
                        "pzn_type": "DE_PZN" if pzn else None
                    }
                )


def downgrade() -> None:
    """Remove migrated product packages."""
    
    # Get connection to execute raw SQL
    connection = op.get_bind()
    
    # Delete product packages that were created from medication N-sizes
    # We identify them by checking if they have the standard N1/N2/N3 package sizes
    connection.execute(
        sa.text("""
            DELETE FROM product_packages 
            WHERE package_size IN ('N1', 'N2', 'N3')
            AND product_id IN (
                SELECT id FROM medication_products 
                WHERE legacy_medication_id IS NOT NULL
            )
        """)
    )
