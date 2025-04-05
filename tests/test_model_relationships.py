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

    def test_medication_inventory_relationship(self):
        """Test the relationship between Medication and Inventory."""
        from app.models import Medication, Inventory

        # Create a medication
        med = Medication(name="Test Med", dosage=1.0, frequency=1.0)
        self.db.session.add(med)
        self.db.session.flush()

        # Create inventory
        inv = Inventory(medication=med, current_count=100)
        self.db.session.add(inv)
        self.db.session.commit()

        # Test the relationship from both sides
        self.assertEqual(med.inventory, inv)
        self.assertEqual(inv.medication, med)

        # Test cascade delete: deleting medication should delete inventory
        self.db.session.delete(med)
        self.db.session.commit()

        # Inventory should be gone
        self.assertEqual(self.db.session.query(Inventory).count(), 0)

    def test_inventory_log_relationship(self):
        """Test the relationship between Inventory and InventoryLog."""
        from app.models import Inventory, InventoryLog, Medication

        # Create a medication and inventory
        med = Medication(name="Test Med", dosage=1.0, frequency=1.0)
        self.db.session.add(med)
        self.db.session.flush()

        inv = Inventory(medication=med, current_count=100)
        self.db.session.add(inv)
        self.db.session.flush()

        # Create inventory logs
        log1 = InventoryLog(
            inventory=inv,
            previous_count=0,
            adjustment=100,
            new_count=100,
            notes="Initial stock",
        )
        self.db.session.add(log1)

        log2 = InventoryLog(
            inventory=inv,
            previous_count=100,
            adjustment=-10,
            new_count=90,
            notes="Used some",
        )
        self.db.session.add(log2)
        self.db.session.commit()

        # Test the relationship
        self.assertEqual(len(inv.inventory_logs), 2)
        self.assertIn(log1, inv.inventory_logs)
        self.assertIn(log2, inv.inventory_logs)

        # Test cascade delete: deleting inventory should delete logs
        self.db.session.delete(inv)
        self.db.session.commit()

        # Logs should be gone
        self.assertEqual(self.db.session.query(InventoryLog).count(), 0)

    def test_medication_schedule_relationship(self):
        """Test the relationship between Medication and MedicationSchedule."""
        from app.models import Medication, MedicationSchedule, ScheduleType

        # Create a medication
        med = Medication(name="Test Med", dosage=1.0, frequency=1.0)
        self.db.session.add(med)
        self.db.session.flush()

        # Create schedules
        schedule1 = MedicationSchedule(
            medication=med,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["08:00"]',
            units_per_dose=1.0,
        )
        self.db.session.add(schedule1)

        schedule2 = MedicationSchedule(
            medication=med,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["20:00"]',
            units_per_dose=1.0,
        )
        self.db.session.add(schedule2)
        self.db.session.commit()

        # Test the relationship
        self.assertEqual(len(med.schedules), 2)
        self.assertIn(schedule1, med.schedules)
        self.assertIn(schedule2, med.schedules)

        # Test cascade delete: deleting medication should delete schedules
        self.db.session.delete(med)
        self.db.session.commit()

        # Schedules should be gone
        self.assertEqual(self.db.session.query(MedicationSchedule).count(), 0)

    def test_hospital_visit_order_relationship(self):
        """Test the relationship between PhysicianVisit and Order."""
        from app.models import PhysicianVisit, Order

        # Create a physician visit
        visit = PhysicianVisit(
            visit_date=self.db.func.current_timestamp(), notes="Test visit"
        )
        self.db.session.add(visit)
        self.db.session.flush()

        # Create orders
        order1 = Order(hospital_visit=visit, status="planned")
        self.db.session.add(order1)

        order2 = Order(hospital_visit=visit, status="printed")
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
        from app.models import Order, OrderItem, Medication, PhysicianVisit

        # Create a visit and order
        visit = PhysicianVisit(
            visit_date=self.db.func.current_timestamp(), notes="Test visit"
        )
        self.db.session.add(visit)
        self.db.session.flush()

        order = Order(hospital_visit=visit, status="planned")
        self.db.session.add(order)
        self.db.session.flush()

        # Create medications
        med1 = Medication(name="Med 1", dosage=1.0, frequency=1.0)
        med2 = Medication(name="Med 2", dosage=2.0, frequency=2.0)
        self.db.session.add_all([med1, med2])
        self.db.session.flush()

        # Create order items
        item1 = OrderItem(
            order=order, medication=med1, quantity_needed=30, packages_n1=1
        )
        self.db.session.add(item1)

        item2 = OrderItem(
            order=order, medication=med2, quantity_needed=60, packages_n2=1
        )
        self.db.session.add(item2)
        self.db.session.commit()

        # Test the relationships
        self.assertEqual(len(order.order_items), 2)
        self.assertIn(item1, order.order_items)
        self.assertIn(item2, order.order_items)

        self.assertEqual(len(med1.order_items), 1)
        self.assertEqual(len(med2.order_items), 1)
        self.assertEqual(med1.order_items[0], item1)
        self.assertEqual(med2.order_items[0], item2)

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

        # Medications should still exist
        self.assertEqual(self.db.session.query(Medication).count(), 2)

    def test_medication_deletion_with_relations(self):
        """Test deleting a medication with various related objects."""
        from app.models import (
            Medication,
            Inventory,
            InventoryLog,
            MedicationSchedule,
            Order,
            OrderItem,
            ScheduleType,
            PhysicianVisit,
        )

        # Create a medication with inventory, logs, schedules, and order items
        med = Medication(name="Complex Med", dosage=1.0, frequency=1.0)
        self.db.session.add(med)
        self.db.session.flush()

        # Add inventory
        inv = Inventory(medication=med, current_count=100)
        self.db.session.add(inv)
        self.db.session.flush()

        # Add inventory log
        log = InventoryLog(
            inventory=inv, previous_count=0, adjustment=100, new_count=100
        )
        self.db.session.add(log)

        # Add schedule
        schedule = MedicationSchedule(
            medication=med,
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

        order = Order(hospital_visit=visit, status="planned")
        self.db.session.add(order)
        self.db.session.flush()

        # Add order item
        item = OrderItem(order=order, medication=med, quantity_needed=30, packages_n1=1)
        self.db.session.add(item)
        self.db.session.commit()

        # Verify relationships
        self.assertEqual(med.inventory, inv)
        self.assertEqual(len(inv.inventory_logs), 1)
        self.assertEqual(len(med.schedules), 1)
        self.assertEqual(len(med.order_items), 1)

        # Deleting medication should:
        # - Delete inventory (cascade)
        # - Delete inventory logs (cascade through inventory)
        # - Delete schedules (cascade)
        # But should NOT delete order items (they should reference None)

        med_id = med.id
        self.db.session.delete(med)
        self.db.session.commit()

        # Verify cascades
        self.assertEqual(
            self.db.session.query(Medication).filter_by(id=med_id).count(), 0
        )
        self.assertEqual(
            self.db.session.query(Inventory).filter_by(medication_id=med_id).count(), 0
        )
        self.assertEqual(
            self.db.session.query(MedicationSchedule)
            .filter_by(medication_id=med_id)
            .count(),
            0,
        )

        # Order item should still exist but have NULL medication_id
        order_item = self.db.session.get(OrderItem, item.id)
        self.assertIsNotNone(order_item)
        self.assertIsNone(order_item.medication)
