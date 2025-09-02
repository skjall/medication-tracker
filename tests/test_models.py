"""
Tests for model classes.

This module contains tests for the various model classes in the application,
focusing on their methods and relationships.
"""

# Standard library imports
import logging
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Third-party imports
import pytz

# Local application imports
from .test_base import BaseTestCase
from app.models import (
    # Old models removed - Inventory and Medication no longer exist
    Physician,
    MedicationSchedule,
    ScheduleType,
    ActiveIngredient,
    MedicationProduct,
)

# Temporarily increase log level
logger = logging.getLogger("app.models")
logger.setLevel(logging.DEBUG)


@unittest.skip("Skipped: Medication model removed")
class TestMedicationSchedule(BaseTestCase):
    """Test cases for the MedicationSchedule model."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a test physician
        self.physician = Physician(
            name="Dr. Test",
            specialty="Cardiology",
            phone="+1-555-0123",
            email="dr.test@example.com"
        )
        self.db.session.add(self.physician)
        self.db.session.commit()

        # Create a test medication for the schedule
        self.medication = Medication(
            name="Test Medication",
            physician_id=self.physician.id,
            is_otc=False,
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

        self.db.session.add(self.medication)
        self.db.session.add(self.schedule)
        self.db.session.commit()

        # Current time and yesterday
        self.yesterday = self.now - timedelta(days=1)

        # Set up utility function mocks
        self.to_local_patcher = patch("app.utils.to_local_timezone")
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
            with patch("app.utils.to_local_timezone") as mock_to_local:
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


@unittest.skip("Skipped: Medication model removed")
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
        MedicationSchedule(
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
        # Test with 175 units needed
        packages = self.medication.calculate_packages_needed(175)

        # Expected solution is 0*N3(500) + 0*N2(100) + 6*N1(30)
        self.assertEqual(packages["N3"], 0)  # No N3 packages (too large)
        self.assertEqual(
            packages["N2"], 0
        )  # No N2 package (2*100 units = 200 units; delta = +25 units)
        self.assertEqual(
            packages["N1"], 6
        )  # 3 N1 packages (6*30 = 180 units; delta = +5 units => Least overshoot)

    def test_calculate_needed_until_visit(self):
        """Test calculation of medication needs until a visit."""

        # Create a visit date 30 days in the future
        # Add some milliseconds to ensure it's after the current date since the actual
        # function will call its own now from datetime and is therefore slightly off
        # which would result in 29 days instead of 30
        visit_date = (
            self.now.astimezone(pytz.timezone("UTC"))
            + timedelta(days=30)
            + timedelta(milliseconds=10)
        )

        logger.info(f"Current date: {self.now.astimezone(pytz.timezone('UTC'))}")
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


@unittest.skip("Skipped: Uses Medication model which was removed")
class TestPhysician(BaseTestCase):
    """Test cases for the Physician model."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

    def test_physician_creation(self):
        """Test creating a physician with all fields."""
        physician = Physician(
            name="Dr. Jane Smith",
            specialty="Endocrinology",
            phone="+1-555-9876",
            email="dr.smith@hospital.com",
            address="123 Medical Center Dr\nSuite 400\nCity, ST 12345",
            notes="Diabetes specialist"
        )
        self.db.session.add(physician)
        self.db.session.commit()

        self.assertIsNotNone(physician.id)
        self.assertEqual(physician.name, "Dr. Jane Smith")
        self.assertEqual(physician.specialty, "Endocrinology")
        self.assertEqual(physician.phone, "+1-555-9876")
        self.assertEqual(physician.email, "dr.smith@hospital.com")
        self.assertIn("Medical Center", physician.address)
        self.assertEqual(physician.notes, "Diabetes specialist")
        self.assertIsNotNone(physician.created_at)
        self.assertIsNotNone(physician.updated_at)

    def test_physician_minimal_creation(self):
        """Test creating a physician with only required fields."""
        physician = Physician(name="Dr. Minimal")
        self.db.session.add(physician)
        self.db.session.commit()

        self.assertIsNotNone(physician.id)
        self.assertEqual(physician.name, "Dr. Minimal")
        self.assertIsNone(physician.specialty)
        self.assertIsNone(physician.phone)
        self.assertIsNone(physician.email)
        self.assertIsNone(physician.address)
        self.assertIsNone(physician.notes)

    def test_physician_display_name_with_specialty(self):
        """Test display_name property with specialty."""
        physician = Physician(
            name="Dr. John Doe",
            specialty="Cardiology"
        )
        self.assertEqual(physician.display_name, "Dr. John Doe (Cardiology)")

    def test_physician_display_name_without_specialty(self):
        """Test display_name property without specialty."""
        physician = Physician(name="Dr. John Doe")
        self.assertEqual(physician.display_name, "Dr. John Doe")

    def test_physician_repr(self):
        """Test string representation of physician."""
        physician = Physician(name="Dr. Test Physician")
        self.assertEqual(repr(physician), "<Physician Dr. Test Physician>")

    def test_physician_medication_relationship(self):
        """Test physician-medication relationship."""
        physician = Physician(name="Dr. Prescriber")
        self.db.session.add(physician)
        self.db.session.commit()

        # Create medications for this physician
        med1 = Medication(
            name="Heart Medicine",
            physician_id=physician.id,
            is_otc=False,
            dosage=1.0,
            frequency=2.0
        )
        med2 = Medication(
            name="Blood Pressure Med",
            physician_id=physician.id,
            is_otc=False,
            dosage=0.5,
            frequency=1.0
        )

        self.db.session.add(med1)
        self.db.session.add(med2)
        self.db.session.commit()

        # Test relationship
        self.assertEqual(len(physician.medications), 2)
        self.assertIn(med1, physician.medications)
        self.assertIn(med2, physician.medications)
        self.assertEqual(med1.physician, physician)
        self.assertEqual(med2.physician, physician)

    def test_medication_without_physician(self):
        """Test medication can exist without a physician."""
        otc_med = Medication(
            name="OTC Pain Relief",
            is_otc=True,
            dosage=500.0,
            frequency=3.0
        )
        self.db.session.add(otc_med)
        self.db.session.commit()

        self.assertIsNone(otc_med.physician_id)
        self.assertIsNone(otc_med.physician)
        self.assertTrue(otc_med.is_otc)

    def test_medication_otc_flag(self):
        """Test medication OTC flag functionality."""
        physician = Physician(name="Dr. OTC Test")
        self.db.session.add(physician)
        self.db.session.commit()

        # Prescribed medication
        prescribed = Medication(
            name="Prescribed Med",
            physician_id=physician.id,
            is_otc=False,
            dosage=1.0,
            frequency=2.0
        )

        # OTC medication
        otc = Medication(
            name="OTC Med",
            is_otc=True,
            dosage=200.0,
            frequency=4.0
        )

        self.db.session.add(prescribed)
        self.db.session.add(otc)
        self.db.session.commit()

        self.assertFalse(prescribed.is_otc)
        self.assertTrue(otc.is_otc)


class TestPhysicianVisit(BaseTestCase):
    """Test cases for PhysicianVisit model with physician relationship."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        self.physician = Physician(
            name="Dr. Visit Test",
            specialty="Family Medicine"
        )
        self.db.session.add(self.physician)
        self.db.session.commit()

    def test_visit_with_physician(self):
        """Test creating a visit with physician."""
        from app.models import PhysicianVisit

        visit = PhysicianVisit(
            physician_id=self.physician.id,
            visit_date=self.now + timedelta(days=30),
            notes="Regular checkup"
        )
        self.db.session.add(visit)
        self.db.session.commit()

        self.assertEqual(visit.physician, self.physician)
        self.assertIn(visit, self.physician.visits)
        self.assertEqual(visit.notes, "Regular checkup")

    def test_visit_without_physician(self):
        """Test creating a visit without physician."""
        from app.models import PhysicianVisit

        visit = PhysicianVisit(
            visit_date=self.now + timedelta(days=15),
            notes="Unassigned visit"
        )
        self.db.session.add(visit)
        self.db.session.commit()

        self.assertIsNone(visit.physician_id)
        self.assertIsNone(visit.physician)

    def test_days_until_calculation(self):
        """Test days until calculation with timezone handling."""
        from app.models import PhysicianVisit

        # Mock current time and settings
        mock_settings = MagicMock()
        mock_settings.timezone_name = 'Europe/Berlin'

        with patch('models.Settings.get_settings', return_value=mock_settings), \
             patch('utils.datetime') as mock_datetime:

            # Set current time to June 3, 2025
            current = datetime(2025, 6, 3, 14, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Visit on June 23, 2025 (20 days later)
            visit_date = datetime(2025, 6, 22, 22, 0, 0, tzinfo=timezone.utc)  # 23.06 00:00 Berlin time

            visit = PhysicianVisit(
                physician_id=self.physician.id,
                visit_date=visit_date,
                notes="Future visit"
            )

            # Test days until calculation
            days = visit.days_until
            self.assertEqual(days, 20, f"Expected 20 days until visit, got {days}")


class TestDateCalculation(BaseTestCase):
    """Test cases for date calculation functions."""

    def test_calculate_days_until_same_day(self):
        """Test calculation for same day."""
        from app.utils import calculate_days_until

        mock_settings = MagicMock()
        mock_settings.timezone_name = 'UTC'

        with patch('models.Settings.get_settings', return_value=mock_settings), \
             patch('app.utils.datetime') as mock_datetime:

            current = datetime(2025, 6, 3, 14, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Same day
            same_day = datetime(2025, 6, 3, 18, 0, 0, tzinfo=timezone.utc)
            self.assertEqual(calculate_days_until(same_day), 0)

    def test_calculate_days_until_tomorrow(self):
        """Test calculation for tomorrow."""
        from app.utils import calculate_days_until

        mock_settings = MagicMock()
        mock_settings.timezone_name = 'UTC'

        with patch('models.Settings.get_settings', return_value=mock_settings), \
             patch('app.utils.datetime') as mock_datetime:

            current = datetime(2025, 6, 3, 14, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Tomorrow
            tomorrow = datetime(2025, 6, 4, 10, 0, 0, tzinfo=timezone.utc)
            self.assertEqual(calculate_days_until(tomorrow), 1)

    def test_calculate_days_until_timezone_handling(self):
        """Test calculation with timezone conversion."""
        from app.utils import calculate_days_until

        mock_settings = MagicMock()
        mock_settings.timezone_name = 'Europe/Berlin'

        with patch('models.Settings.get_settings', return_value=mock_settings), \
             patch('app.utils.datetime') as mock_datetime:

            # Current time: June 3, 2025 14:00 UTC (16:00 Berlin time)
            current = datetime(2025, 6, 3, 14, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Target: June 23, 2025 22:00 UTC (00:00 June 24 Berlin time, but date is June 23)
            target = datetime(2025, 6, 22, 22, 0, 0, tzinfo=timezone.utc)  # This is June 23 midnight Berlin

            days = calculate_days_until(target)
            self.assertEqual(days, 20, f"Expected 20 days, got {days}")
