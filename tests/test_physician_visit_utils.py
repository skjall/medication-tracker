"""
Tests for physician visit utilities.

This module tests functions related to physician visit scheduling,
interval calculations, and automatic inventory deduction.
"""

# Standard library imports
import logging
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Third-party imports
import pytz
import tzlocal

# Local application imports
from .test_base import BaseTestCase

# Temporarily increase log level
logger = logging.getLogger("test.physician_visit_utils")
logger.setLevel(logging.DEBUG)


class TestPhysicianVisitUtils(BaseTestCase):
    """Test cases for physician visit utility functions."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Import models after app context is created
        from app.models import (
            MedicationSchedule,
            ScheduleType,
            ActiveIngredient,
            ProductPackage,
            ScannedItem,
            PackageInventory,
            Settings,
            PhysicianVisit,
        )

        self.MedicationSchedule = MedicationSchedule
        self.ScheduleType = ScheduleType
        self.ActiveIngredient = ActiveIngredient
        self.ProductPackage = ProductPackage
        self.ScannedItem = ScannedItem
        self.PackageInventory = PackageInventory
        self.Settings = Settings
        self.PhysicianVisit = PhysicianVisit

        # Import here to avoid issues with app context
        from app.physician_visit_utils import (
            calculate_estimated_next_visit_date,
            calculate_days_between_visits,
            auto_deduct_inventory,
        )

        # Save references to the functions for testing
        self.calculate_estimated_next_visit_date = calculate_estimated_next_visit_date
        self.calculate_days_between_visits = calculate_days_between_visits
        self.auto_deduct_inventory = auto_deduct_inventory

    def tearDown(self):
        """Clean up after each test."""
        # Roll back the session to clean up all test data
        self.db.session.rollback()
        super().tearDown()

    def test_calculate_estimated_next_visit_date(self):
        """Test estimating the next visit date based on settings."""
        # Create test settings for this test only
        settings = self.Settings(
            default_visit_interval=90,
            auto_schedule_visits=True,
            default_order_for_next_but_one=True,
            timezone_name="UTC",
        )
        self.db.session.add(settings)
        self.db.session.commit()

        # Test with default from_date (current date)
        next_date = self.calculate_estimated_next_visit_date()

        # Should be 90 days in the future (default interval)
        expected_date = self.now.astimezone(pytz.timezone("UTC")) + timedelta(days=90)
        delta = abs((next_date - expected_date).total_seconds())
        self.assertLess(delta, 5)  # Allow 5 seconds difference

        # Test with custom from_date
        from_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        next_date = self.calculate_estimated_next_visit_date(from_date)

        # Should be 90 days after from_date
        expected_date = from_date + timedelta(days=90)
        self.assertEqual(next_date.date(), expected_date.date())

    def test_calculate_days_between_visits(self):
        """Test calculating the average days between visits."""
        # Create test settings for this test only
        settings = self.Settings(
            default_visit_interval=90,
            auto_schedule_visits=True,
            default_order_for_next_but_one=True,
            timezone_name="UTC",
        )
        self.db.session.add(settings)

        # Create physician visits specific to this test
        visit1 = self.PhysicianVisit(
            visit_date=self.now - timedelta(days=90), notes="Past visit 1"
        )
        visit2 = self.PhysicianVisit(
            visit_date=self.now - timedelta(days=45), notes="Past visit 2"
        )
        visit3 = self.PhysicianVisit(
            visit_date=self.now + timedelta(days=45), notes="Upcoming visit"
        )
        self.db.session.add_all([settings, visit1, visit2, visit3])
        self.db.session.commit()

        # With our test data, we have 2 intervals:
        # visit1 to visit2: 45 days
        # visit2 to visit3: 90 days
        # Average: (45 + 90) / 2 = 67.5 days, rounded to 67
        result = self.calculate_days_between_visits()
        self.assertEqual(result, 67)

        # Test with no visits - first clean up existing visits
        self.db.session.delete(visit1)
        self.db.session.delete(visit2)
        self.db.session.delete(visit3)
        self.db.session.commit()

        # Should fall back to settings default
        result = self.calculate_days_between_visits()
        self.assertEqual(result, 90)

    def test_disabled_auto_deduction(self):
        """Test that auto-deduction respects the enabled flag."""
        # Create active ingredient with auto-deduction disabled for this test only
        ingredient = self.ActiveIngredient(
            name="Test Ingredient", auto_deduction_enabled=False
        )
        self.db.session.add(ingredient)
        self.db.session.flush()  # Get ID without committing

        # Create a scanned item - use unique identifiers
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
        test_gtin = f"123456789{unique_suffix.zfill(4)}"
        
        scanned_item = self.ScannedItem(
            gtin=test_gtin,
            serial_number=f"TEST{unique_suffix}",
            batch_number="BATCH001",
            status="active"
        )
        self.db.session.add(scanned_item)
        self.db.session.flush()

        inventory = self.PackageInventory(
            scanned_item=scanned_item,
            current_units=100,
            original_units=100,
            status="sealed"
        )
        self.db.session.add(inventory)

        schedule = self.MedicationSchedule(
            active_ingredient=ingredient,
            schedule_type=self.ScheduleType.DAILY,
            times_of_day='["08:00", "18:00"]',
            units_per_dose=2.0,
            last_deduction=self.now - timedelta(days=1),
        )
        self.db.session.add(schedule)
        self.db.session.commit()

        # Mock is_due_now to return True
        with patch("app.models.MedicationSchedule.is_due_now", return_value=True):
            # Run the deduction
            deduction_count = self.auto_deduct_inventory()

            # No ingredients should have been processed
            self.assertEqual(deduction_count, 0)

            # Inventory should remain unchanged
            self.db.session.refresh(inventory)
            self.assertEqual(inventory.current_units, 100)
