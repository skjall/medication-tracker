"""
Unit tests for the models file


"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

# Add app to path for imports
path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
if path not in sys.path:
    sys.path.insert(0, path)

# Import the models to test
from models import MedicationSchedule, ScheduleType


class TestIsDueNow(unittest.TestCase):
    """Test cases for the is_due_now method in MedicationSchedule."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a mock schedule
        self.schedule = MagicMock(spec=MedicationSchedule)

        self.schedule.is_due_now = MedicationSchedule.is_due_now.__get__(
            self.schedule, MedicationSchedule
        )

        # Set up schedule data
        self.schedule.formatted_times = ["08:00", "18:00"]
        self.schedule.formatted_weekdays = [0, 2, 4]  # Mon, Wed, Fri
        self.schedule.interval_days = 1
        self.schedule.schedule_type = ScheduleType.DAILY

        # Current time and last deduction
        self.now = datetime.now(timezone.utc)
        self.yesterday = self.now - timedelta(days=1)
        self.schedule.last_deduction = None

        # Set up utility function mocks
        self.to_local_patcher = patch("utils.to_local_timezone")
        self.mock_to_local = self.to_local_patcher.start()

        # By default, make the local time the same as UTC for testing simplicity
        self.mock_to_local.side_effect = lambda dt: dt

    def tearDown(self):
        """Clean up after each test."""
        self.to_local_patcher.stop()

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
        self.schedule.formatted_weekdays = [0, 2, 4]  # Mon(0), Wed(2), Fri(4)

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


if __name__ == "__main__":
    unittest.main()
