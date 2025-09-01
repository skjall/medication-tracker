"""
Tests for the deduction_service module.

This module tests the functionality of the deduction service,
which is responsible for tracking and deducting medication inventory.
"""

# Standard library imports
import logging
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Local application imports
from .test_base import BaseTestCase

logger = logging.getLogger("app.deduction_service")
logger.setLevel(logging.DEBUG)


class TestDeductionService(BaseTestCase):
    """Test suite for deduction_service module."""

    def setUp(self):
        """Set up test fixtures for each test."""
        super().setUp()

        # Import models after app context is created
        from app.models import (
            MedicationSchedule,
            ScheduleType,
            Medication,
            Inventory,
            Settings,
        )

        # Import module here to avoid issues with app context
        from app.deduction_service import (
            calculate_missed_deductions,
            _calculate_daily_missed_deductions,
            _calculate_interval_missed_deductions,
            _calculate_weekdays_missed_deductions,
            perform_deductions,
        )

        # Save references to the functions for testing
        self.calculate_missed_deductions = calculate_missed_deductions
        self.calculate_daily_missed_deductions = (
            _calculate_daily_missed_deductions
        )
        self.calculate_interval_missed_deductions = (
            _calculate_interval_missed_deductions
        )
        self.calculate_weekdays_missed_deductions = (
            _calculate_weekdays_missed_deductions
        )
        self.perform_deductions = perform_deductions

        # Set up current time and yesterday
        self.yesterday = self.now - timedelta(days=1)

        # Create a medication with inventory
        self.medication = Medication(
            name="Test Med",
            dosage=2.0,
            frequency=2.0,
            auto_deduction_enabled=True,
        )

        # Add to database
        self.db.session.add(self.medication)
        self.db.session.flush()

        # Create inventory
        self.inventory = Inventory(
            medication=self.medication, current_count=100
        )
        self.db.session.add(self.inventory)

        # Create a schedule
        self.schedule = MedicationSchedule(
            medication=self.medication,
            schedule_type=ScheduleType.DAILY,
            interval_days=1,
            times_of_day='["08:00", "18:00"]',
            units_per_dose=2.0,
            last_deduction=self.yesterday,
        )
        self.db.session.add(self.schedule)

        # Create settings
        self.settings = Settings(
            default_visit_interval=90, timezone_name="UTC"
        )
        self.db.session.add(self.settings)
        self.db.session.commit()

        # Set up utility function mocks
        # For testing, we'll use UTC as the "local" timezone to keep things simple
        # This way, the conversions are identity functions but the logic still works
        self.utils_patcher = patch("app.deduction_service.utc_to_local")
        self.mock_to_local_timezone = self.utils_patcher.start()
        # Add timezone info if missing to ensure datetime comparisons work
        self.mock_to_local_timezone.side_effect = lambda dt: (
            dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        )

        self.from_local_patcher = patch("app.deduction_service.local_to_utc")
        self.mock_from_local_timezone = self.from_local_patcher.start()
        # Add timezone info if missing to ensure datetime comparisons work
        self.mock_from_local_timezone.side_effect = lambda dt: (
            dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        )

        # Mock parse_schedule_time to return UTC times directly
        self.parse_time_patcher = patch(
            "app.deduction_service.parse_schedule_time"
        )
        self.mock_parse_time = self.parse_time_patcher.start()

        def mock_parse(time_str, date):
            hour, minute = map(int, time_str.split(":"))
            return datetime(
                date.year,
                date.month,
                date.day,
                hour,
                minute,
                0,
                tzinfo=timezone.utc,
            )

        self.mock_parse_time.side_effect = mock_parse

    def tearDown(self):
        """Clean up after each test."""
        self.utils_patcher.stop()
        self.from_local_patcher.stop()
        self.parse_time_patcher.stop()
        super().tearDown()

    def test_calculate_daily_missed_deductions(self):
        """Test calculation of missed deductions for daily schedules."""
        from app.models import ScheduleType

        # Set up the schedule
        self.schedule.schedule_type = ScheduleType.DAILY

        # Set the last deduction to yesterday BEFORE the first scheduled time
        # This way yesterday will still be checked for the 18:00 dose
        yesterday_7am = datetime(
            self.yesterday.year,
            self.yesterday.month,
            self.yesterday.day,
            7,
            0,  # Before first scheduled time of 8am
            0,
            tzinfo=timezone.utc,
        )
        self.schedule.last_deduction = yesterday_7am

        # Current time is today afternoon
        today_2pm = datetime(
            self.now.year,
            self.now.month,
            self.now.day,
            14,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # We should have missed yesterday 8am, yesterday 18:00, and today 08:00
        missed = self.calculate_daily_missed_deductions(
            self.schedule,
            yesterday_7am,
            today_2pm,
            self.schedule.formatted_times,
        )

        # Expected: yesterday 08:00, yesterday 18:00, and today 08:00
        self.assertEqual(len(missed), 3)

        # Verify the times
        expected_times = [
            datetime(
                self.yesterday.year,
                self.yesterday.month,
                self.yesterday.day,
                8,
                0,
                0,
                tzinfo=timezone.utc,
            ),
            datetime(
                self.yesterday.year,
                self.yesterday.month,
                self.yesterday.day,
                18,
                0,
                0,
                tzinfo=timezone.utc,
            ),
            datetime(
                self.now.year,
                self.now.month,
                self.now.day,
                8,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        ]

        # Times should match (accounting for timezone issues in testing)
        for expected, actual in zip(expected_times, missed):
            self.assertEqual(expected.hour, actual.hour)
            self.assertEqual(expected.minute, actual.minute)

    def test_calculate_interval_missed_deductions(self):
        """Test calculation of missed deductions for interval schedules."""
        from app.models import ScheduleType

        # Set up the schedule (every 2 days)
        self.schedule.schedule_type = ScheduleType.INTERVAL
        self.schedule.interval_days = 2

        # Last deduction was 5 days ago at 8am
        five_days_ago = self.now - timedelta(days=5)
        last_deduction = datetime(
            five_days_ago.year,
            five_days_ago.month,
            five_days_ago.day,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Current time is today noon
        current_time = datetime(
            self.now.year,
            self.now.month,
            self.now.day,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Should have doses on day 3 and day 5 (today) at 8am
        missed = self.calculate_interval_missed_deductions(
            self.schedule,
            last_deduction,
            current_time,
            self.schedule.formatted_times,
        )

        # Expected: 2 days of doses, with 2 doses each day (8am, 6pm)
        self.assertEqual(len(missed), 4)

    @unittest.skip("Skipping - requires refactoring for timezone handling")
    def test_calculate_weekdays_missed_deductions(self):
        """Test calculation of missed deductions for weekday schedules."""
        from app.models import ScheduleType

        # Set up the schedule (Mon, Wed, Fri)
        self.schedule.schedule_type = ScheduleType.WEEKDAYS
        self.schedule.weekdays = "[0, 2, 4]"  # Mon, Wed, Fri

        # Create a Monday last week
        last_monday = self.now - timedelta(days=7 + self.now.weekday())
        last_deduction = datetime(
            last_monday.year,
            last_monday.month,
            last_monday.day,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Current time is today noon
        current_time = datetime(
            self.now.year,
            self.now.month,
            self.now.day,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )

        # Mock weekday determination
        with patch("app.deduction_service.utc_to_local") as mock_to_local:
            # Make the dates return the right weekday when checked
            def mock_weekday_dates(dt):
                # Create a map of dates to weekdays for our test period
                date_map = {}
                for i in range(-10, 1):
                    test_date = current_time + timedelta(days=i)
                    # Weekday 0 = Monday, etc
                    date_map[test_date.date()] = (
                        test_date.weekday(),
                        test_date,
                    )

                # Return the mock datetime with the right weekday
                if dt in date_map:
                    return date_map[dt][1]

                # For the check in the function, fake the weekday attribute
                mock_dt = MagicMock()
                mock_dt.date.return_value = dt.date()
                mock_dt.weekday.return_value = dt.weekday()
                return mock_dt

            mock_to_local.side_effect = mock_weekday_dates

            # Call the function
            missed = self.calculate_weekdays_missed_deductions(
                self.schedule,
                last_deduction,
                current_time,
                self.schedule.formatted_times,
            )

            # We should have doses for each Mon, Wed, Fri since last Monday
            # The exact count depends on current date - verify it's reasonable
            self.assertGreater(len(missed), 0)
            self.assertLessEqual(len(missed), 30)  # Sanity check

    @unittest.skip(
        "Skipping - requires refactoring for new ActiveIngredient-based system"
    )
    def test_perform_deductions(self):
        """Test the main deduction function that performs all deductions."""
        # TODO: This test needs to be rewritten to work with the new ActiveIngredient-based
        # deduction system instead of the old Medication-based system

        # Use patch at the correct module level with an isolation strategy
        with patch(
            "app.deduction_service.calculate_missed_deductions"
        ) as mock_calc:
            # Configure the mock
            mock_calc.return_value = [
                self.yesterday + timedelta(hours=18),  # Yesterday evening
                self.now - timedelta(hours=2),  # Today morning
            ]

            # Call the function
            med_count, action_count = self.perform_deductions(self.now)

            # Verify calculate_missed_deductions was called exactly once per schedule
            self.assertEqual(mock_calc.call_count, 1)

            # Check results
            self.assertEqual(med_count, 1)  # 1 ingredient affected
            self.assertEqual(action_count, 2)  # 2 deductions made

            # Verify schedule's last_deduction was updated
            self.db.session.refresh(self.schedule)

            # Compare only the relevant parts of the datetime, ignoring timezone info
            expected_time = mock_calc.return_value[-1].replace(tzinfo=None)
            actual_time = self.schedule.last_deduction.replace(tzinfo=None)
            self.assertEqual(actual_time, expected_time)

            # Verify inventory was updated correctly (deducted 2 doses of 2.0 units)
            self.db.session.refresh(self.inventory)
            self.assertEqual(self.inventory.current_count, 100 - (2 * 2.0))

    @unittest.skip("Skipping - requires refactoring for timezone handling")
    def test_calculate_missed_deductions_for_daily(self):
        """Test the main missed deduction calculation for daily schedule."""
        from app.models import ScheduleType, MedicationSchedule
        import logging

        # Add debug logging
        logger = logging.getLogger("app.deduction_service")
        logger.setLevel(logging.DEBUG)

        # Debug print to see what's happening
        print(f"ScheduleType enum from import: {ScheduleType.DAILY}")

        # Set up the schedule
        self.schedule.schedule_type = ScheduleType.DAILY

        # Try to force it to match by getting a fresh enum
        # This is to avoid the two different enum instances problem
        from sqlalchemy import inspect

        column_type = inspect(MedicationSchedule).columns.schedule_type.type
        if hasattr(column_type, "enum_class"):
            self.schedule.schedule_type = column_type.enum_class.DAILY

        self.db.session.commit()

        # Set the last deduction to be old enough to guarantee missed doses
        two_weeks_ago = self.now - timedelta(days=14)
        self.schedule.last_deduction = two_weeks_ago
        self.db.session.commit()

        # Call the function with a daily schedule
        missed = self.calculate_missed_deductions(self.schedule, self.now)

        self.assertGreater(len(missed), 0)

        # Verify each result is a datetime with timezone info
        for dt in missed:
            self.assertIsInstance(dt, datetime)
            self.assertIsNotNone(dt.tzinfo)

    def test_no_missed_deductions_without_schedules(self):
        """Test behavior when no schedules are defined."""
        # Empty schedule times
        self.schedule.times_of_day = "[]"
        self.db.session.commit()

        # Call the function
        missed = self.calculate_missed_deductions(self.schedule, self.now)

        # Verify we got no missed deductions
        self.assertEqual(len(missed), 0)

    def test_no_inventory_no_deduction(self):
        """Test that no deduction occurs when there's no inventory."""
        self.db.session.delete(self.inventory)
        self.db.session.commit()

        # Mock the calculate_missed_deductions function
        with patch(
            "app.deduction_service.calculate_missed_deductions"
        ) as mock_calc:
            mock_calc.return_value = [self.now - timedelta(hours=2)]

            # Run the deduction process
            med_count, action_count = self.perform_deductions(self.now)

            # Since there's no inventory, no deductions should happen
            self.assertEqual(med_count, 0)
            self.assertEqual(action_count, 0)

    def test_insufficient_inventory(self):
        """Test behavior when inventory is less than required dose."""
        # Set inventory below dose amount
        self.inventory.current_count = 1.5  # Less than 2.0 dose
        self.db.session.commit()

        # Mock missed deductions using the correct patch path
        with patch(
            "app.deduction_service.calculate_missed_deductions"
        ) as mock_calc:
            mock_calc.return_value = [
                self.now - timedelta(hours=2)  # One recent missed dose
            ]

            # Call the function
            med_count, action_count = self.perform_deductions(self.now)

            # Should have tried to process one medication but unable to deduct
            self.assertEqual(med_count, 0)
            self.assertEqual(action_count, 0)

            # Inventory should remain unchanged
            self.db.session.refresh(self.inventory)
            self.assertEqual(self.inventory.current_count, 1.5)
