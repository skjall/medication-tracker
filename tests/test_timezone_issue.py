"""
Simple test to reproduce the specific timezone issue reported.
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from .test_base import BaseTestCase
from app.models import PhysicianVisit, Physician
from app.utils import to_local_timezone, from_local_timezone, format_date


class TestTimezoneIssue(BaseTestCase):
    """Test the specific timezone issue where 23.06.2025 becomes 22.06.2025."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.physician = Physician(name="Dr. Test", specialty="Cardiology")
        self.db.session.add(self.physician)
        self.db.session.commit()

    def test_europe_berlin_date_display_issue(self):
        """Test the specific issue with Europe/Berlin timezone showing wrong date."""
        # Mock the settings to return Europe/Berlin timezone
        mock_settings = MagicMock()
        mock_settings.timezone_name = 'Europe/Berlin'
        
        with patch('models.Settings.get_settings', return_value=mock_settings):
            # Create a naive datetime representing the user's input: 23.06.2025
            user_input_date = datetime(2025, 6, 23, 0, 0, 0)  # Midnight local time
            
            # Convert to UTC for storage (this is what the application does)
            utc_date = from_local_timezone(user_input_date)
            print(f"User input: {user_input_date}")
            print(f"Stored UTC: {utc_date}")
            
            # Create visit
            visit = PhysicianVisit(
                physician_id=self.physician.id,
                visit_date=utc_date,
                notes="Test visit for timezone issue"
            )
            self.db.session.add(visit)
            self.db.session.commit()
            
            # Test 1: Check what format_date returns (this should work correctly)
            formatted_date = format_date(visit.visit_date)
            print(f"format_date result: {formatted_date}")
            self.assertEqual(formatted_date, "23.06.2025", 
                           f"format_date should return 23.06.2025, got {formatted_date}")
            
            # Test 2: Check what direct strftime returns (this is the bug)
            direct_strftime = visit.visit_date.strftime('%d.%m.%Y')
            print(f"Direct strftime result: {direct_strftime}")
            # This will likely show 22.06.2025, demonstrating the bug
            
            # Test 3: Check local timezone conversion
            local_datetime = to_local_timezone(visit.visit_date)
            local_date_str = local_datetime.strftime('%d.%m.%Y')
            print(f"Local timezone conversion: {local_date_str}")
            self.assertEqual(local_date_str, "23.06.2025",
                           f"Local timezone conversion should return 23.06.2025, got {local_date_str}")

    def test_multiple_timezones_consistency(self):
        """Test that the same local date works consistently across different timezones."""
        test_cases = [
            ('UTC', '23.06.2025'),
            ('Europe/Berlin', '23.06.2025'),     # UTC+2 in summer
            ('America/New_York', '23.06.2025'),  # UTC-4 in summer  
            ('Asia/Tokyo', '23.06.2025'),        # UTC+9
        ]
        
        for tz_name, expected_date in test_cases:
            with self.subTest(timezone=tz_name):
                mock_settings = MagicMock()
                mock_settings.timezone_name = tz_name
                
                with patch('models.Settings.get_settings', return_value=mock_settings):
                    # User enters 23.06.2025 in their local timezone
                    user_input = datetime(2025, 6, 23, 0, 0, 0)
                    
                    # Convert to UTC for storage
                    utc_date = from_local_timezone(user_input)
                    
                    # Create visit
                    visit = PhysicianVisit(
                        physician_id=self.physician.id,
                        visit_date=utc_date,
                        notes=f"Test for {tz_name}"
                    )
                    self.db.session.add(visit)
                    self.db.session.commit()
                    
                    # Test that format_date returns the correct date
                    formatted = format_date(visit.visit_date)
                    self.assertEqual(formatted, expected_date,
                                   f"Timezone {tz_name}: expected {expected_date}, got {formatted}")
                    
                    # Test that direct strftime is different (showing the bug)
                    direct = visit.visit_date.strftime('%d.%m.%Y')
                    if tz_name != 'UTC':
                        # For non-UTC timezones, direct strftime will likely show wrong date
                        print(f"{tz_name}: format_date={formatted}, direct_strftime={direct}")
                    
                    # Clean up
                    self.db.session.delete(visit)
                    self.db.session.commit()

    def test_dst_summer_vs_winter(self):
        """Test DST handling for summer vs winter dates."""
        mock_settings = MagicMock()
        mock_settings.timezone_name = 'Europe/Berlin'
        
        with patch('models.Settings.get_settings', return_value=mock_settings):
            test_dates = [
                (datetime(2025, 6, 23, 0, 0, 0), "23.06.2025"),  # Summer (DST)
                (datetime(2025, 1, 23, 0, 0, 0), "23.01.2025"),  # Winter (no DST)
            ]
            
            for user_input, expected in test_dates:
                with self.subTest(date=expected):
                    # Convert to UTC
                    utc_date = from_local_timezone(user_input)
                    
                    # Create visit
                    visit = PhysicianVisit(
                        physician_id=self.physician.id,
                        visit_date=utc_date,
                        notes=f"DST test for {expected}"
                    )
                    self.db.session.add(visit)
                    self.db.session.commit()
                    
                    # Test formatting
                    formatted = format_date(visit.visit_date)
                    self.assertEqual(formatted, expected,
                                   f"DST test failed: expected {expected}, got {formatted}")
                    
                    # Show the difference between correct and incorrect formatting
                    direct = visit.visit_date.strftime('%d.%m.%Y')
                    print(f"Date {expected}: format_date={formatted}, direct_strftime={direct}")
                    
                    # Clean up
                    self.db.session.delete(visit)
                    self.db.session.commit()


if __name__ == '__main__':
    unittest.main()