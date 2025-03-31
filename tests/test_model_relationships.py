"""
Tests for hospital visit utilities.

This module tests functions related to hospital visit scheduling,
interval calculations, and automatic inventory deduction.
"""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from .test_base import BaseTestCase
from app.models import (
    HospitalVisit,
    HospitalVisitSettings,
    Medication,
    Inventory,
    MedicationSchedule,
    ScheduleType,
    db,
)


class TestHospitalVisitUtils(BaseTestCase):
    """Test cases for hospital visit utility functions."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Import here to avoid issues with app context
        from app.hospital_visit_utils import (
            calculate_estimated_next_visit_date,
            calculate_days_between_visits,
            auto_deduct_inventory,
        )

        # Save references to the functions for testing
        self.calculate_estimated_next_visit_date = calculate_estimated_next_visit_date
        self.calculate_days_between_visits = calculate_days_between_visits
        self.auto_deduct_inventory = auto_deduct_inventory

        # Create test settings
        self.settings = HospitalVisitSettings(
            default_visit_interval=90,
            auto_schedule_visits=True,
            default_order_for_next_but_one=True,
            timezone_name="UTC",
        )
        db.session.add(self.settings)

        # Create a few visits
        now = datetime.now(timezone.utc)

        # Past visits
        self.visit1 = HospitalVisit(
            visit_date=now - timedelta(days=90), notes="Past visit 1"
        )

        self.visit2 = HospitalVisit(
            visit_date=now - timedelta(days=45), notes="Past visit 2"
        )

        # Upcoming visit
        self.visit3 = HospitalVisit(
            visit_date=now + timedelta(days=45), notes="Upcoming visit"
        )

        db.session.add_all([self.visit1, self.visit2, self.visit3])
        db.session.commit()

        # Create medication with schedule for auto-deduction testing
        self.medication = Medication(
            name="Test Med", dosage=2.0, frequency=2.0, auto_deduction_enabled=True
        )
        db.session.add(self.medication)

        # Create inventory
        self.inventory = Inventory(medication=self.medication, current_count=100)
        db.session.add(self.inventory)

        # Create a schedule due now
        self.now = datetime.now(timezone.utc)
        self.schedule = MedicationSchedule(
            medication=self.medication,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["08:00", "18:00"]',
            units_per_dose=2.0,
        )
        db.session.add(self.schedule)
        db.session.commit()

    def test_calculate_estimated_next_visit_date(self):
        """Test estimating the next visit date based on settings."""
        # Test with default from_date (current date)
        next_date = self.calculate_estimated_next_visit_date()

        # Should be 90 days in the future (default interval)
        expected_date = datetime.now(timezone.utc) + timedelta(days=90)
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
        # With our test data, we have 2 intervals:
        # visit1 to visit2: 45 days
        # visit2 to visit3: 90 days
        # Average: (45 + 90) / 2 = 67.5 days, rounded to 67

        result = self.calculate_days_between_visits()
        self.assertEqual(result, 67)

        # Test with no visits
        db.session.delete(self.visit1)
        db.session.delete(self.visit2)
        db.session.delete(self.visit3)
        db.session.commit()

        # Should fall back to settings default
        result = self.calculate_days_between_visits()
        self.assertEqual(result, 90)

    def test_auto_deduct_inventory(self):
        """Test automatic inventory deduction."""
        # Setup the schedule to be due now
        # Mock is_due_now to return True
        with patch("models.MedicationSchedule.is_due_now", return_value=True):
            # Run the deduction
            deduction_count = self.auto_deduct_inventory()

            # Should have processed one medication
            self.assertEqual(deduction_count, 1)

            # Verify inventory was deducted
            db.session.refresh(self.inventory)
            self.assertEqual(self.inventory.current_count, 98.0)  # 100 - 2.0

            # Verify last deduction was updated
            db.session.refresh(self.schedule)
            self.assertIsNotNone(self.schedule.last_deduction)

    def test_disabled_auto_deduction(self):
        """Test that auto-deduction respects the enabled flag."""
        # Disable auto-deduction
        self.medication.auto_deduction_enabled = False
        db.session.commit()

        # Mock is_due_now to return True
        with patch("models.MedicationSchedule.is_due_now", return_value=True):
            # Run the deduction
            deduction_count = self.auto_deduct_inventory()

            # No medications should have been processed
            self.assertEqual(deduction_count, 0)

            # Inventory should remain unchanged
            db.session.refresh(self.inventory)
            self.assertEqual(self.inventory.current_count, 100)


if __name__ == "__main__":
    unittest.main()
