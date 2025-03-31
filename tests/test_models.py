"""
Tests for model classes.

This module contains tests for the various model classes in the application,
focusing on their methods and relationships.
"""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import pytz

from .test_base import BaseTestCase
from app.models import (
    Medication,
    Inventory,
    MedicationSchedule,
    ScheduleType,
)


import logging

# Temporarily increase log level
logger = logging.getLogger("app.models")
logger.setLevel(logging.DEBUG)


class TestMedicationSchedule(BaseTestCase):
    """Test cases for the MedicationSchedule model."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a test medication for the schedule
        self.medication = Medication(
            name="Test Medication",
            dosage=2.0,
            frequency=2.0,
            package_size_n1=30,
            package_size_n2=100,
            min_threshold=20,
            safety_margin_days=14,
        )

        # Create a schedule attached to the medication
        self.schedule = MedicationSchedule(
            medication=self.medication,
            schedule_type=ScheduleType.DAILY,
            interval_days=1,
            times_of_day='["08:00", "18:00"]',
            units_per_dose=1.5,
        )

        # Current time and yesterday
        self.yesterday = self.now - timedelta(days=1)

        # Set up utility function mocks
        self.to_local_patcher = patch("utils.to_local_timezone")
        self.mock_to_local = self.to_local_patcher.start()

        # By default, make the local time the same as UTC for testing simplicity
        self.mock_to_local.side_effect = lambda dt: dt

    def tearDown(self):
        """Clean up after each test."""
        self.to_local_patcher.stop()
        super().tearDown()

    def test_exact_time_match(self):
        """Test that exactly matching a scheduled time returns True."""
        # Set current time to exactly 8:00
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 0, 0, tzinfo=timezone.utc
        )

        # Should be due
        result = self.schedule.is_due_now(current_time)
        self.assertTrue(result)

    def test_near_time_match(self):
        """Test that being close to a scheduled time returns True."""
        # Set current time to 8:03 (within 5 minutes of 8:00)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 3, 0, tzinfo=timezone.utc
        )

        # Should be due
        result = self.schedule.is_due_now(current_time)
        self.assertTrue(result)

        # Set current time to 7:57 (within 5 minutes of 8:00)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 7, 57, 0, tzinfo=timezone.utc
        )

        # Should be due
        result = self.schedule.is_due_now(current_time)
        self.assertTrue(result)

    def test_time_too_far(self):
        """Test that being too far from a scheduled time returns False."""
        # Set current time to 8:06 (more than 5 minutes from 8:00)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 6, 0, tzinfo=timezone.utc
        )

        # Should not be due
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

        # Set current time to 7:54 (more than 5 minutes from 8:00)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 7, 54, 0, tzinfo=timezone.utc
        )

        # Should not be due
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

    def test_already_deducted_today(self):
        """Test that having already deducted today returns False."""
        # Set last deduction to today at 8:00
        self.schedule.last_deduction = datetime(
            self.now.year, self.now.month, self.now.day, 8, 0, 0, tzinfo=timezone.utc
        )

        # Set current time to 8:03 (within 5 minutes)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 3, 0, tzinfo=timezone.utc
        )

        # Should not be due since we already deducted
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

    def test_deducted_different_time_slot(self):
        """Test that having deducted a different time slot today returns True."""
        # Set last deduction to today at 8:00
        self.schedule.last_deduction = datetime(
            self.now.year, self.now.month, self.now.day, 8, 0, 0, tzinfo=timezone.utc
        )

        # Set current time to 18:00 (a different time slot)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 18, 0, 0, tzinfo=timezone.utc
        )

        # Should be due since it's a different time slot
        result = self.schedule.is_due_now(current_time)
        self.assertTrue(result)

    def test_interval_schedule(self):
        """Test interval schedule behavior."""
        # Set schedule to interval (every 2 days)
        self.schedule.schedule_type = ScheduleType.INTERVAL
        self.schedule.interval_days = 2

        # Set last deduction to yesterday at 8:00
        self.schedule.last_deduction = datetime(
            self.yesterday.year,
            self.yesterday.month,
            self.yesterday.day,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Set current time to today at 8:00
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 0, 0, tzinfo=timezone.utc
        )

        # Should not be due since it's only been 1 day (needs 2)
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

        # Set last deduction to 2 days ago
        two_days_ago = self.now - timedelta(days=2)
        self.schedule.last_deduction = datetime(
            two_days_ago.year,
            two_days_ago.month,
            two_days_ago.day,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Should be due now
        result = self.schedule.is_due_now(current_time)
        self.assertTrue(result)

    def test_weekdays_schedule(self):
        """Test weekday schedule behavior."""
        # Set schedule to weekdays (Mon, Wed, Fri)
        self.schedule.schedule_type = ScheduleType.WEEKDAYS
        self.schedule.weekdays = "[0, 2, 4]"  # Mon(0), Wed(2), Fri(4)

        # Test with different weekdays
        for weekday in range(7):  # 0-6 (Mon-Sun)
            # Set up a time for the given weekday
            test_date = self.now
            while test_date.weekday() != weekday:
                test_date += timedelta(days=1)

            current_time = datetime(
                test_date.year,
                test_date.month,
                test_date.day,
                8,
                0,
                0,
                tzinfo=timezone.utc,
            )

            # Mock the weekday check
            with patch("utils.to_local_timezone") as mock_to_local:
                mock_dt = MagicMock()
                mock_dt.date.return_value = current_time.date()
                mock_dt.weekday.return_value = weekday
                mock_dt.strftime.return_value = "08:00"
                mock_to_local.return_value = mock_dt

                # Should be due only on Mon, Wed, Fri
                expected = weekday in [0, 2, 4]
                result = self.schedule.is_due_now(current_time)
                self.assertEqual(result, expected, f"Failed for weekday {weekday}")

    def test_same_time_slot_flexibility(self):
        """Test the 5-minute flexibility in time slot checking."""
        # Set last deduction to today at 8:02
        self.schedule.last_deduction = datetime(
            self.now.year, self.now.month, self.now.day, 8, 2, 0, tzinfo=timezone.utc
        )

        # Set current time to 8:04 (within 5 minutes of last deduction)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 4, 0, tzinfo=timezone.utc
        )

        # Should not be due since it's considered the same time slot
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

        # Set current time to 8:08 (more than 5 minutes from last deduction)
        current_time = datetime(
            self.now.year, self.now.month, self.now.day, 8, 8, 0, tzinfo=timezone.utc
        )

        # This is tricky - it's not in the same time slot as the last deduction (8:02),
        # but it's also not within 5 minutes of a scheduled time (8:00).
        # The expected behavior is False (not due)
        result = self.schedule.is_due_now(current_time)
        self.assertFalse(result)

    def test_calculate_daily_usage_daily(self):
        """Test calculation of daily usage for daily schedule."""
        # Set a daily schedule with 2 doses per day, 1.5 units per dose
        self.schedule.schedule_type = ScheduleType.DAILY
        self.schedule.times_of_day = '["08:00", "18:00"]'
        self.schedule.units_per_dose = 1.5

        # Expected: 2 times * 1.5 units = 3 units per day
        self.assertEqual(self.schedule.calculate_daily_usage(), 3.0)

    def test_calculate_daily_usage_interval(self):
        """Test calculation of daily usage for interval schedule."""
        # Set an interval schedule (every 2 days) with 2 doses per day, 1.5 units per dose
        self.schedule.schedule_type = ScheduleType.INTERVAL
        self.schedule.interval_days = 2
        self.schedule.times_of_day = '["08:00", "18:00"]'
        self.schedule.units_per_dose = 1.5

        # Expected: (2 times * 1.5 units) / 2 days = 1.5 units per day
        self.assertEqual(self.schedule.calculate_daily_usage(), 1.5)

    def test_calculate_daily_usage_weekdays(self):
        """Test calculation of daily usage for weekday schedule."""
        # Set a weekday schedule (3 days per week) with 2 doses per day, 1.5 units per dose
        self.schedule.schedule_type = ScheduleType.WEEKDAYS
        self.schedule.weekdays = "[0, 2, 4]"  # Mon, Wed, Fri (3 days)
        self.schedule.times_of_day = '["08:00", "18:00"]'
        self.schedule.units_per_dose = 1.5

        # Expected: (2 times * 1.5 units * 3 days) / 7 days = 1.29 units per day
        self.assertAlmostEqual(self.schedule.calculate_daily_usage(), 1.29, places=2)


class TestMedication(BaseTestCase):
    """Test cases for the Medication model."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a test medication with inventory
        self.medication = Medication(
            name="Test Medication",
            dosage=2.0,
            frequency=2.0,
            package_size_n1=30,
            package_size_n2=100,
            package_size_n3=500,
            min_threshold=20,
            safety_margin_days=14,
        )

        # Create inventory
        self.inventory = Inventory(medication=self.medication, current_count=100)

        # Create a schedule
        self.schedule = MedicationSchedule(
            medication=self.medication,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["08:00", "18:00"]',
            units_per_dose=1.5,
        )

    def test_daily_usage_calculation(self):
        """Test that daily usage is calculated correctly from schedules."""
        # Expected: 2 times per day * 1.5 units = 3.0 units per day
        self.assertEqual(self.medication.daily_usage, 3.0)

        # Add another schedule
        schedule2 = MedicationSchedule(
            medication=self.medication,
            schedule_type=ScheduleType.DAILY,
            times_of_day='["12:00"]',
            units_per_dose=1.0,
        )

        # Expected: (2 times * 1.5 units) + (1 time * 1.0 units) = 4.0 units per day
        self.assertEqual(self.medication.daily_usage, 4.0)

    def test_days_remaining_calculation(self):
        """Test that days remaining is calculated correctly."""
        # With 100 units and usage of 3.0 units per day, should have 33.33 days
        self.assertAlmostEqual(self.medication.days_remaining, 33.33, places=2)

        # Change inventory to test different values
        self.inventory.current_count = 50
        # With 50 units and usage of 3.0 units per day, should have 16.67 days
        self.assertAlmostEqual(self.medication.days_remaining, 16.67, places=2)

    def test_depletion_date_calculation(self):
        """Test that depletion date is calculated correctly."""
        # With current usage and inventory, should deplete in about 33.33 days
        days_remaining = self.medication.days_remaining
        expected_date = self.now.astimezone(pytz.timezone("UTC")) + timedelta(
            days=days_remaining
        )

        # Should be within a small delta (seconds difference due to test execution time)
        delta = abs((expected_date - self.medication.depletion_date).total_seconds())
        self.assertLess(delta, 5)  # Allow 5 seconds difference

    def test_calculate_packages_needed(self):
        """Test that package calculation works correctly."""
        # Test with 175 units needed - should prefer larger packages
        packages = self.medication.calculate_packages_needed(175)

        # Expected optimal solution is 1*N3(500) + 1*N2(100) + 0*N1(30)
        self.assertEqual(packages["N3"], 0)  # No N3 packages (too large)
        self.assertEqual(packages["N2"], 1)  # 1 N2 package (100 units)
        self.assertEqual(packages["N1"], 3)  # 3 N1 packages (3*30 = 90 units)

        # Total: 100 + 90 = 190 units (>= 175 needed)

    def test_calculate_needed_until_visit(self):
        """Test calculation of medication needs until a visit."""

        # Create a visit date 30 days in the future
        visit_date = self.now.astimezone(pytz.timezone("UTC")) + timedelta(days=30)

        logger.info(f"Current date: {self.now.astimezone(pytz.timezone("UTC"))}")
        logger.info(f"Visit date: {visit_date}")

        # Calculate needs without safety margin
        needed = self.medication.calculate_needed_until_visit(
            visit_date, include_safety_margin=False, consider_next_but_one=False
        )

        # Expected: 30 days * 3.0 units per dose = 90 units
        self.assertEqual(needed, 90)

        # Calculate needs with safety margin (14 days)
        needed_with_margin = self.medication.calculate_needed_until_visit(
            visit_date, include_safety_margin=True, consider_next_but_one=False
        )

        # Expected: (30 days + 14 days) * 3.0 units per day = 132 units
        self.assertEqual(needed_with_margin, 132)
