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
    Physician,
    MedicationSchedule,
    ScheduleType,
    ActiveIngredient,
    MedicationProduct,
)

# Temporarily increase log level
logger = logging.getLogger("app.models")
logger.setLevel(logging.DEBUG)


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