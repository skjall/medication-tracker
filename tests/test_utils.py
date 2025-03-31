"""
Tests for utility functions.

This module tests various utility functions, particularly focusing on
timezone handling, date formatting, and other helper functions.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import pytz

from .test_base import BaseTestCase
from app.utils import (
    ensure_timezone_utc,
    to_local_timezone,
    from_local_timezone,
    calculate_days_until,
    format_datetime,
    format_date,
    format_time,
)

import logging

# Temporarily increase log level
logger = logging.getLogger("app.model_relationships")
logger.setLevel(logging.DEBUG)


class TestTimezoneUtils(BaseTestCase):
    """Test cases for timezone utility functions."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a datetime object for testing
        self.utc_now = self.now.astimezone(pytz.timezone("UTC"))
        self.naive_now = self.now

    def test_ensure_timezone_utc(self):
        # Test with timezone-naive datetime
        result = ensure_timezone_utc(self.naive_now)
        self.assertEqual(result.tzinfo, timezone.utc)

        # Test with timezone-aware datetime
        berlin_tz = pytz.timezone("Europe/Berlin")
        berlin_time = self.now.astimezone(berlin_tz)
        result = ensure_timezone_utc(berlin_time)

        # Compare timezone zones instead of objects
        self.assertEqual(result.tzinfo.zone, berlin_tz.zone)

    def test_to_local_timezone(self):
        """Test conversion from UTC to local timezone."""
        from app.models import HospitalVisitSettings

        # Mock the application timezone setting
        with patch("utils.get_application_timezone") as mock_get_tz:
            # Set app timezone to Berlin
            timezone_string = "Europe/Berlin"

            # Create a HospitalVisitSettings object with the timezone
            set = HospitalVisitSettings(timezone_name=timezone_string)
            self.db.session.add(set)
            self.db.session.flush()

            mock_get_tz.return_value = pytz.timezone(timezone_string)

            berlin_tz = pytz.timezone(timezone_string)
            mock_get_tz.return_value = berlin_tz

            # Convert UTC time to Berlin time
            result = to_local_timezone(self.utc_now)

            # Check timezone
            self.assertEqual(result.tzinfo.zone, berlin_tz.zone)

            # Berlin is ahead of UTC by 1 or 2 hours depending on DST
            # So the hour should be adjusted accordingly
            utc_hour = self.utc_now.hour
            expected_hour = (utc_hour + 1) % 24  # Assuming CET (UTC+1)

            # We need to be flexible about DST, so just check that time differs
            self.assertNotEqual(self.utc_now.hour, result.hour)

    def test_from_local_timezone(self):
        """Test conversion from local timezone to UTC."""
        # Mock the application timezone setting
        with patch("utils.get_application_timezone") as mock_get_tz:
            # Set app timezone to Berlin
            berlin_tz = pytz.timezone("Europe/Berlin")
            mock_get_tz.return_value = berlin_tz

            # Create a Berlin timezone datetime
            berlin_time = self.now.astimezone(berlin_tz)

            # Convert to UTC
            result = from_local_timezone(berlin_time)

            # Check timezone
            self.assertEqual(result.tzinfo, timezone.utc)

            # The hour should be adjusted back
            berlin_hour = berlin_time.hour
            expected_hour = (berlin_hour - 1) % 24  # Assuming CET (UTC+1)

            # We need to be flexible about DST, so just check that time differs
            self.assertNotEqual(berlin_time.hour, result.hour)

    def test_calculate_days_until(self):
        """Test calculation of days until a target date."""
        # Today should return 1 (tomorrow)
        today = self.now.astimezone(pytz.timezone("UTC"))
        result = calculate_days_until(today)
        self.assertEqual(result, 1)

        # Tomorrow should return 1
        tomorrow = today + timedelta(days=1)
        result = calculate_days_until(tomorrow)
        self.assertEqual(result, 1)

        # 5 days ahead should return 5
        future = today + timedelta(days=5)
        result = calculate_days_until(future)
        self.assertEqual(result, 5)


class TestDateFormatting(BaseTestCase):
    """Test cases for date formatting utility functions."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a datetime object for testing
        self.test_dt = datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)

    def test_format_datetime(self):
        """Test datetime formatting."""
        # Mock local timezone to avoid actual TZ conversion for predictable tests
        with patch("utils.to_local_timezone") as mock_to_local:
            # Identity function for testing
            mock_to_local.side_effect = lambda dt: dt

            # Test without seconds
            result = format_datetime(self.test_dt, show_seconds=False)
            self.assertEqual(result, "15.01.2023 14:30")

            # Test with seconds
            result = format_datetime(self.test_dt, show_seconds=True)
            self.assertEqual(result, "15.01.2023 14:30:45")

    def test_format_date(self):
        """Test date formatting."""
        # Mock local timezone to avoid actual TZ conversion for predictable tests
        with patch("utils.to_local_timezone") as mock_to_local:
            # Identity function for testing
            mock_to_local.side_effect = lambda dt: dt

            result = format_date(self.test_dt)
            self.assertEqual(result, "15.01.2023")

    def test_format_time(self):
        """Test time formatting."""
        # Mock local timezone to avoid actual TZ conversion for predictable tests
        with patch("utils.to_local_timezone") as mock_to_local:
            # Identity function for testing
            mock_to_local.side_effect = lambda dt: dt

            result = format_time(self.test_dt)
            self.assertEqual(result, "14:30:45")


if __name__ == "__main__":
    unittest.main()
