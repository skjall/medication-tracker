"""
Test inventory logging functionality.
"""

import unittest
from datetime import datetime, timezone
from .test_base import BaseTestCase


class TestInventoryLogging(BaseTestCase):
    """Test suite for inventory logging functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Import models after app context is created
        from app.models import (
            ActiveIngredient,
            MedicationProduct, 
            ProductPackage,
            ScannedItem,
            PackageInventory,
            InventoryLog
        )

        # Create test data
        self.ingredient = ActiveIngredient(name="Test Ingredient")
        self.db.session.add(self.ingredient)
        self.db.session.flush()

        self.product = MedicationProduct(
            active_ingredient=self.ingredient,
            brand_name="Test Product"
        )
        self.db.session.add(self.product)
        self.db.session.flush()

        # Use unique GTIN for each test
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]
        test_gtin = f"123456789{unique_suffix.zfill(4)}"
        
        self.package = ProductPackage(
            product=self.product,
            package_size="N1",
            quantity=100,
            gtin=test_gtin
        )
        self.db.session.add(self.package)
        self.db.session.flush()

        self.scanned_item = ScannedItem(
            gtin=test_gtin,
            serial_number=f"TEST{unique_suffix}",
            batch_number="BATCH001",
            status="active"
        )
        self.db.session.add(self.scanned_item)
        self.db.session.flush()

        self.inventory = PackageInventory(
            scanned_item=self.scanned_item,
            current_units=100,
            original_units=100,
            status="sealed"
        )
        self.db.session.add(self.inventory)
        self.db.session.commit()

    def test_log_onboarding(self):
        """Test logging when a package is onboarded."""
        from app.models import InventoryLog
        
        # Log onboarding
        self.inventory.log_onboarding("Test onboarding")
        self.db.session.commit()
        
        # Check log was created
        log = InventoryLog.query.filter_by(package_inventory_id=self.inventory.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.change_type, 'onboarded')
        self.assertEqual(log.units_before, 0)
        self.assertEqual(log.units_after, 100)
        self.assertEqual(log.units_changed, 100)
        self.assertEqual(log.reason, "Test onboarding")

    def test_log_deduction(self):
        """Test logging when units are deducted."""
        from app.models import InventoryLog
        
        # Deduct units and log
        old_units = self.inventory.current_units
        self.inventory.current_units -= 10
        self.inventory.log_deduction(10, "Test deduction")
        self.db.session.commit()
        
        # Check log was created
        log = InventoryLog.query.filter_by(package_inventory_id=self.inventory.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.change_type, 'deducted')
        self.assertEqual(log.units_before, 100)
        self.assertEqual(log.units_after, 90)
        self.assertEqual(log.units_changed, -10)
        self.assertEqual(log.reason, "Test deduction")

    def test_display_properties(self):
        """Test display properties work correctly."""
        from app.models import InventoryLog
        
        # Create a log entry
        self.inventory.log_deduction(5, "Test")
        self.db.session.commit()
        
        log = InventoryLog.query.filter_by(package_inventory_id=self.inventory.id).first()
        
        # Test display properties
        self.assertEqual(log.display_change_type, "Deducted")
        self.assertEqual(log.units_display, "-5.0")

    def test_multiple_logs_ordering(self):
        """Test that multiple logs are ordered correctly."""
        from app.models import InventoryLog
        
        # Create multiple log entries
        self.inventory.log_onboarding("First log")
        self.db.session.commit()
        
        # Wait a tiny bit to ensure different timestamps
        import time
        time.sleep(0.01)
        
        self.inventory.current_units -= 10
        self.inventory.log_deduction(10, "Second log")
        self.db.session.commit()
        
        # Check logs are in correct order (newest first)
        logs = (
            InventoryLog.query
            .filter_by(package_inventory_id=self.inventory.id)
            .order_by(InventoryLog.changed_at.desc())
            .all()
        )
        
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].change_type, 'deducted')  # Most recent
        self.assertEqual(logs[1].change_type, 'onboarded')  # Oldest


if __name__ == '__main__':
    unittest.main()