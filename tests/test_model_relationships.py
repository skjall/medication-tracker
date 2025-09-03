"""
Tests for model relationships.

This module tests the relationships between different model classes,
ensuring cascades, back references, and constraints work correctly.
"""

# Standard library imports
import logging

# Local application imports
from .test_base import BaseTestCase

# Temporarily increase log level
logger = logging.getLogger("app.model_relationships")
logger.setLevel(logging.DEBUG)


class TestModelRelationships(BaseTestCase):
    """Test cases for model relationships."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

    def test_ingredient_inventory_relationship_simple(self):
        """Test the relationship between ActiveIngredient and package inventories."""
        from app.models import ActiveIngredient

        # Create an active ingredient
        ingredient = ActiveIngredient(name="Test Ingredient")
        self.db.session.add(ingredient)
        self.db.session.commit()

        # Test that the property works (even if empty)
        package_inventories = ingredient.package_inventories
        self.assertEqual(len(package_inventories), 0)
        
        # Test basic ingredient properties
        self.assertEqual(ingredient.total_inventory_count, 0)
        self.assertIsNone(ingredient.days_remaining)

    def test_ingredient_product_relationship(self):
        """Test the relationship between ActiveIngredient and MedicationProduct."""
        from app.models import ActiveIngredient, MedicationProduct

        # Create an active ingredient
        ingredient = ActiveIngredient(name="Test Ingredient")
        self.db.session.add(ingredient)
        self.db.session.flush()

        # Create products
        product1 = MedicationProduct(
            active_ingredient=ingredient,
            brand_name="Brand A"
        )
        product2 = MedicationProduct(
            active_ingredient=ingredient,
            brand_name="Brand B"
        )
        self.db.session.add_all([product1, product2])
        self.db.session.commit()

        # Test the relationship
        self.assertEqual(len(ingredient.products), 2)
        self.assertIn(product1, ingredient.products)
        self.assertIn(product2, ingredient.products)
        self.assertEqual(product1.active_ingredient, ingredient)
        self.assertEqual(product2.active_ingredient, ingredient)

        # Test cascade delete: deleting ingredient should delete products
        self.db.session.delete(ingredient)
        self.db.session.commit()

        # Products should be gone
        self.assertEqual(self.db.session.query(MedicationProduct).count(), 0)

    def test_ingredient_schedule_relationship(self):
        """Test the relationship between ActiveIngredient and MedicationSchedule."""
        from app.models import ActiveIngredient, MedicationSchedule, ScheduleType

        # Create an active ingredient
        ingredient = ActiveIngredient(name="Test Ingredient")
        self.db.session.add(ingredient)
        self.db.session.flush()

        # Create schedules
        schedule1 = MedicationSchedule(
            active_ingredient=ingredient,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["08:00"]',
            units_per_dose=1.0,
        )
        self.db.session.add(schedule1)

        schedule2 = MedicationSchedule(
            active_ingredient=ingredient,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["20:00"]',
            units_per_dose=1.0,
        )
        self.db.session.add(schedule2)
        self.db.session.commit()

        # Test the relationship
        self.assertEqual(len(ingredient.schedules), 2)
        self.assertIn(schedule1, ingredient.schedules)
        self.assertIn(schedule2, ingredient.schedules)

        # Test cascade delete: deleting ingredient should delete schedules
        self.db.session.delete(ingredient)
        self.db.session.commit()

        # Schedules should be gone
        self.assertEqual(self.db.session.query(MedicationSchedule).count(), 0)

    def test_physician_visit_order_relationship(self):
        """Test the relationship between PhysicianVisit and Order."""
        from app.models import PhysicianVisit, Order

        # Create a physician visit
        visit = PhysicianVisit(
            visit_date=self.db.func.current_timestamp(), notes="Test visit"
        )
        self.db.session.add(visit)
        self.db.session.flush()

        # Create orders
        order1 = Order(physician_visit=visit, status="planned")
        self.db.session.add(order1)

        order2 = Order(physician_visit=visit, status="printed")
        self.db.session.add(order2)
        self.db.session.commit()

        # Test the relationship
        self.assertEqual(len(visit.orders), 2)
        self.assertIn(order1, visit.orders)
        self.assertIn(order2, visit.orders)

        # Test cascade delete: deleting visit should delete orders
        self.db.session.delete(visit)
        self.db.session.commit()

        # Orders should be gone
        self.assertEqual(self.db.session.query(Order).count(), 0)

    def test_order_orderitem_relationship(self):
        """Test the relationship between Order and OrderItem."""
        from app.models import Order, OrderItem, ActiveIngredient, MedicationProduct, PhysicianVisit

        # Create a visit and order
        visit = PhysicianVisit(
            visit_date=self.db.func.current_timestamp(), notes="Test visit"
        )
        self.db.session.add(visit)
        self.db.session.flush()

        order = Order(physician_visit=visit, status="planned")
        self.db.session.add(order)
        self.db.session.flush()

        # Create active ingredients and products
        ingredient1 = ActiveIngredient(name="Ingredient 1")
        ingredient2 = ActiveIngredient(name="Ingredient 2")
        self.db.session.add_all([ingredient1, ingredient2])
        self.db.session.flush()
        
        product1 = MedicationProduct(
            active_ingredient=ingredient1,
            brand_name="Product 1"
        )
        product2 = MedicationProduct(
            active_ingredient=ingredient2,
            brand_name="Product 2"
        )
        self.db.session.add_all([product1, product2])
        self.db.session.flush()

        # Create order items
        item1 = OrderItem(
            order=order, active_ingredient=ingredient1, product=product1, quantity_needed=30, packages_n1=1
        )
        self.db.session.add(item1)

        item2 = OrderItem(
            order=order, active_ingredient=ingredient2, product=product2, quantity_needed=60, packages_n2=1
        )
        self.db.session.add(item2)
        self.db.session.commit()

        # Test the relationships
        self.assertEqual(len(order.order_items), 2)
        self.assertIn(item1, order.order_items)
        self.assertIn(item2, order.order_items)

        self.assertEqual(len(ingredient1.order_items), 1)
        self.assertEqual(len(ingredient2.order_items), 1)
        self.assertEqual(ingredient1.order_items[0], item1)
        self.assertEqual(ingredient2.order_items[0], item2)

        logger.debug(
            f"Orders before deletion: {self.db.session.query(OrderItem).all()}"
        )

        # Test cascade delete: deleting order should delete items
        self.db.session.delete(order)
        self.db.session.commit()

        # Verify that the order is gone
        logger.debug(f"Orders after deletion: {self.db.session.query(OrderItem).all()}")

        # After deleting the order
        remaining_items = self.db.session.query(OrderItem).all()
        if remaining_items:
            logger.info(f"Remaining items: {remaining_items}")
            logger.debug(f"Item order_id: {remaining_items[0].order_id}")
        else:
            logger.debug("No remaining items found.")

        # Items should be gone
        self.assertEqual(self.db.session.query(OrderItem).count(), 0)

        # Active ingredients should still exist
        self.assertEqual(self.db.session.query(ActiveIngredient).count(), 2)

    def test_ingredient_deletion_with_relations(self):
        """Test deleting an active ingredient with various related objects."""
        from app.models import (
            ActiveIngredient,
            MedicationProduct,
            ProductPackage,
            ScannedItem,
            PackageInventory,
            MedicationSchedule,
            Order,
            OrderItem,
            ScheduleType,
            PhysicianVisit,
        )

        # Create an active ingredient with products, inventory, schedules, and order items
        ingredient = ActiveIngredient(name="Complex Ingredient")
        self.db.session.add(ingredient)
        self.db.session.flush()

        # Add product
        product = MedicationProduct(
            active_ingredient=ingredient,
            brand_name="Test Product"
        )
        self.db.session.add(product)
        self.db.session.flush()

        # Create a product package - use unique GTINs  
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
        test_gtin = f"123456789{unique_suffix.zfill(4)}"
        
        package = ProductPackage(
            product=product,
            package_size="N1",
            quantity=30,
            gtin=test_gtin
        )
        self.db.session.add(package)
        self.db.session.flush()

        # Create a scanned item
        scanned_item = ScannedItem(
            gtin=test_gtin,
            serial_number=f"TEST{unique_suffix}",
            batch_number="BATCH001",
            status="active"
        )
        self.db.session.add(scanned_item)
        self.db.session.flush()

        # Add inventory
        inv = PackageInventory(
            scanned_item=scanned_item,
            current_units=30,
            original_units=30,
            status="sealed"
        )
        self.db.session.add(inv)
        self.db.session.flush()

        # Add schedule
        schedule = MedicationSchedule(
            active_ingredient=ingredient,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["08:00"]',
            units_per_dose=1.0,
        )
        self.db.session.add(schedule)

        # Create a visit and order
        visit = PhysicianVisit(
            visit_date=self.db.func.current_timestamp(), notes="Test visit"
        )
        self.db.session.add(visit)
        self.db.session.flush()

        order = Order(physician_visit=visit, status="planned")
        self.db.session.add(order)
        self.db.session.flush()

        # Add order item
        item = OrderItem(order=order, active_ingredient=ingredient, product=product, quantity_needed=30, packages_n1=1)
        self.db.session.add(item)
        self.db.session.commit()

        # Verify relationships
        self.assertEqual(len(ingredient.products), 1)
        self.assertEqual(len(ingredient.package_inventories), 1)
        self.assertEqual(len(ingredient.schedules), 1)
        self.assertEqual(len(ingredient.order_items), 1)

        # Deleting ingredient should:
        # - Delete products (cascade)
        # - Delete inventory (cascade)
        # - Delete schedules (cascade)
        # But should NOT delete order items (they should reference None)

        ingredient_id = ingredient.id
        self.db.session.delete(ingredient)
        self.db.session.commit()

        # Verify cascades
        self.assertEqual(
            self.db.session.query(ActiveIngredient).filter_by(id=ingredient_id).count(), 0
        )
        self.assertEqual(
            self.db.session.query(MedicationProduct).filter_by(active_ingredient_id=ingredient_id).count(), 0
        )
        # Package inventory remains (it's linked to scanned items, not directly to ingredient)
        self.assertEqual(
            self.db.session.query(PackageInventory).count(), 1
        )
        self.assertEqual(
            self.db.session.query(MedicationSchedule)
            .filter_by(active_ingredient_id=ingredient_id)
            .count(),
            0,
        )

        # Order item should still exist but linked to None
        order_item = self.db.session.get(OrderItem, item.id)
        self.assertIsNotNone(order_item)
        self.assertIsNone(order_item.active_ingredient_id)
