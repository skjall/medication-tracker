import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

# Add app to path for imports
path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
sys.path.insert(0, path)


# Import necessary modules
from main import create_app
from models import MedicationSchedule, ScheduleType, Medication, Inventory
from deduction_service import (
    _calculate_daily_missed_deductions,
    _calculate_interval_missed_deductions,
    _calculate_weekdays_missed_deductions,
    calculate_missed_deductions,
    perform_deductions,
)


class TestIsDueNow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test app and push an application context
        cls.app = create_app({"TESTING": True})
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        # Pop the application context
        cls.app_context.pop()

    def setUp(self):
        # Reset database
        from models import db

        print("Path added to sys.path:", path)

        db.session.remove()
        db.drop_all()
        db.create_all()

        # Set up current time and yesterday
        self.now = datetime.now(timezone.utc)
        self.yesterday = self.now - timedelta(days=1)

        # Create a mock schedule
        from unittest.mock import MagicMock

        self.schedule = MagicMock(spec=MedicationSchedule)
        self.schedule.formatted_times = ["08:00", "18:00"]
        self.schedule.last_deduction = self.yesterday
        self.schedule.interval_days = 1
        self.schedule.formatted_weekdays = [0, 2, 4]  # Mon, Wed, Fri
        self.schedule.units_per_dose = 2.0

        # Create a mock medication
        self.medication = MagicMock(spec=Medication)
        self.medication.name = "Test Med"
        self.medication.auto_deduction_enabled = True

        self.medication.schedules = [self.schedule]

        # Create a mock inventory
        self.inventory = MagicMock(spec=Inventory)
        self.inventory.current_count = 100
        self.medication.inventory = self.inventory

        # Set up utility function mocks
        self.utils_patcher = patch("deduction_service.to_local_timezone")
        self.mock_to_local_timezone = self.utils_patcher.start()
        self.mock_to_local_timezone.side_effect = (
            lambda dt: dt
        )  # Identity function for testing

        self.from_local_patcher = patch("deduction_service.from_local_timezone")
        self.mock_from_local_timezone = self.from_local_patcher.start()
        self.mock_from_local_timezone.side_effect = (
            lambda dt: dt
        )  # Identity function for testing

    def tearDown(self):
        """Clean up after each test."""
        self.utils_patcher.stop()
        self.from_local_patcher.stop()

    def test_calculate_daily_missed_deductions(self):
        """Test calculation of missed deductions for daily schedules."""
        # Set up the schedule
        self.schedule.schedule_type = ScheduleType.DAILY

        # Set the last deduction to yesterday morning
        yesterday_8am = datetime(
            self.yesterday.year,
            self.yesterday.month,
            self.yesterday.day,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        )
        self.schedule.last_deduction = yesterday_8am

        # Current time is today afternoon
        today_2pm = datetime(
            self.now.year, self.now.month, self.now.day, 14, 0, 0, tzinfo=timezone.utc
        )

        # We should have missed yesterday evening and today morning doses
        missed = _calculate_daily_missed_deductions(
            self.schedule, yesterday_8am, today_2pm, self.schedule.formatted_times
        )

        # Expected: yesterday 18:00 and today 08:00
        self.assertEqual(len(missed), 2)

        # Verify the times
        expected_times = [
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
            self.now.year, self.now.month, self.now.day, 12, 0, 0, tzinfo=timezone.utc
        )

        # Should have doses on day 3 and day 5 (today) at 8am
        missed = _calculate_interval_missed_deductions(
            self.schedule, last_deduction, current_time, self.schedule.formatted_times
        )

        # Expected: 2 days of doses, with 2 doses each day (8am, 6pm)
        self.assertEqual(len(missed), 4)

    def test_calculate_weekdays_missed_deductions(self):
        """Test calculation of missed deductions for weekday schedules."""
        # Set up the schedule (Mon, Wed, Fri)
        self.schedule.schedule_type = ScheduleType.WEEKDAYS
        self.schedule.formatted_weekdays = [0, 2, 4]  # Mon, Wed, Fri

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
            self.now.year, self.now.month, self.now.day, 12, 0, 0, tzinfo=timezone.utc
        )

        # Mock weekday determination
        with patch("deduction_service.to_local_timezone") as mock_to_local:
            # Make the dates return the right weekday when checked
            def mock_weekday_dates(dt):
                # Create a map of dates to weekdays for our test period
                date_map = {}
                for i in range(-10, 1):
                    test_date = current_time + timedelta(days=i)
                    # Weekday 0 = Monday, etc
                    date_map[test_date.date()] = (test_date.weekday(), test_date)

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
            missed = _calculate_weekdays_missed_deductions(
                self.schedule,
                last_deduction,
                current_time,
                self.schedule.formatted_times,
            )

            # We should have doses for each Mon, Wed, Fri since last Monday
            # The exact count depends on current date - verify it's reasonable
            self.assertGreater(len(missed), 0)
            self.assertLessEqual(len(missed), 30)  # Sanity check

    @patch("deduction_service.db.session")
    def test_perform_deductions(self, mock_session):
        """Test the main deduction function that performs all deductions."""
        # Set up expectations
        self.medication.auto_deduction_enabled = True

        # Mock the database query
        with patch("deduction_service.Medication.query") as mock_query:
            mock_query.filter_by.return_value.all.return_value = [self.medication]

            # Mock calculate_missed_deductions to return 2 missed doses
            with patch("deduction_service.calculate_missed_deductions") as mock_calc:
                mock_calc.return_value = [
                    self.yesterday + timedelta(hours=18),  # Yesterday evening
                    self.now - timedelta(hours=2),  # Today morning
                ]

                # Call the function
                med_count, action_count = perform_deductions(self.now)

                # Check results
                self.assertEqual(med_count, 1)  # 1 medication affected
                self.assertEqual(action_count, 2)  # 2 deductions made

                # Verify inventory was updated correctly
                self.assertEqual(self.inventory.update_count.call_count, 2)

                # Verify last_deduction was updated
                self.assertEqual(
                    self.schedule.last_deduction, mock_calc.return_value[-1]
                )

                # Verify session commit was called
                mock_session.commit.assert_called()

    def test_calculate_missed_deductions_for_daily(self):
        """Test the main missed deduction calculation for daily schedule."""
        self.schedule.schedule_type = ScheduleType.DAILY

        with patch(
            "deduction_service._calculate_daily_missed_deductions"
        ) as mock_daily:
            mock_daily.return_value = [
                self.yesterday + timedelta(hours=18),
                self.now - timedelta(hours=4),
            ]

            # Call the function
            missed = calculate_missed_deductions(self.schedule, self.now)

            # Verify the right sub-function was called
            mock_daily.assert_called_once()

            # Verify we got the expected result
            self.assertEqual(len(missed), 2)
            self.assertEqual(missed, mock_daily.return_value)

    def test_no_missed_deductions_without_schedules(self):
        """Test behavior when no schedules are defined."""
        # Empty schedule times
        self.schedule.formatted_times = []

        # Call the function
        with patch(
            "deduction_service._calculate_daily_missed_deductions"
        ) as mock_daily:
            mock_daily.return_value = []

            # Call the function
            missed = calculate_missed_deductions(self.schedule, self.now)

            # Verify we got no missed deductions
            self.assertEqual(len(missed), 0)


if __name__ == "__main__":
    unittest.main()
