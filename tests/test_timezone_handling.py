"""
Tests for timezone handling across the medication tracker application.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from .test_base import BaseTestCase
from app.models import PhysicianVisit, Medication, Physician
from app.utils import to_local_timezone, from_local_timezone, format_date, format_datetime


class TestTimezoneHandling(BaseTestCase):
    """Test timezone handling across different timezones and DST scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.sample_physician = Physician(name="Dr. Test", specialty="Cardiology")
        self.db.session.add(self.sample_physician)
        self.db.session.commit()

    def test_timezone_conversion_utilities(self):
        """Test core timezone conversion utilities."""
        # Test UTC datetime
        utc_dt = datetime(2025, 6, 23, 22, 0, 0, tzinfo=timezone.utc)

        # Test basic timezone conversion
        with patch('models.Settings.get_settings') as mock_settings:
            mock_settings.return_value.timezone_name = 'UTC'
            local_dt = to_local_timezone(utc_dt)
            # UTC to UTC should be the same
            assert local_dt.replace(tzinfo=None) == utc_dt.replace(tzinfo=None)

        with patch('models.Settings.get_settings') as mock_settings:
            mock_settings.return_value.timezone_name = 'Europe/Berlin'
            local_dt = to_local_timezone(utc_dt)
            # Should be converted to Berlin time (UTC+2 in summer)
            assert local_dt.hour == 0  # 22:00 UTC + 2 hours = 00:00 next day

    def test_visit_date_storage_and_retrieval(self):
        """Test that visit dates are stored and retrieved correctly across timezones."""
        test_timezones = [
            'UTC',
            'Europe/Berlin',  # UTC+1/+2 with DST
            'America/New_York',  # UTC-5/-4 with DST
            'Asia/Tokyo',  # UTC+9 no DST
            'Australia/Sydney',  # UTC+10/+11 with DST (opposite hemisphere)
        ]

        # Test dates in both summer (DST) and winter (no DST)
        test_dates = [
            datetime(2025, 6, 23, 0, 0, 0),  # Summer date
            datetime(2025, 1, 15, 0, 0, 0),  # Winter date
        ]

        for tz_name in test_timezones:
            for test_date in test_dates:
                with patch('models.Settings.get_settings') as mock_settings:
                    mock_settings.return_value.timezone_name = tz_name

                    # Create visit with local date
                    utc_date = from_local_timezone(test_date)
                    visit = PhysicianVisit(
                        physician_id=self.sample_physician.id,
                        visit_date=utc_date,
                        notes=f"Test visit {tz_name} {test_date.strftime('%Y-%m-%d')}"
                    )
                    self.db.session.add(visit)
                    self.db.session.commit()

                    # Retrieve and verify the date displays correctly
                    retrieved_visit = self.db.session.get(PhysicianVisit, visit.id)
                    local_date = to_local_timezone(retrieved_visit.visit_date)

                    # The displayed date should match the original input date
                    assert local_date.date() == test_date.date(), \
                        f"Date mismatch for {tz_name} on {test_date.date()}: got {local_date.date()}"

                    # Test format_date function
                    formatted = format_date(retrieved_visit.visit_date)
                    expected_format = test_date.strftime('%d.%m.%Y')
                    assert formatted == expected_format, \
                        f"Format mismatch for {tz_name}: got {formatted}, expected {expected_format}"

                    # Clean up
                    self.db.session.delete(visit)
                    self.db.session.commit()

    def test_dst_transition_dates(self):
        """Test timezone handling around DST transition dates."""
        # Test Europe/Berlin DST transitions for 2025
        dst_test_cases = [
            # DST begins: last Sunday in March (March 30, 2025)
            ('Europe/Berlin', datetime(2025, 3, 29, 23, 0, 0)),  # Before DST
            ('Europe/Berlin', datetime(2025, 3, 30, 3, 0, 0)),   # After DST transition
            # DST ends: last Sunday in October (October 26, 2025)
            ('Europe/Berlin', datetime(2025, 10, 25, 23, 0, 0)),  # Before DST ends
            ('Europe/Berlin', datetime(2025, 10, 26, 3, 0, 0)),  # After DST ends

            # Test US EST/EDT transitions for 2025
            # DST begins: second Sunday in March (March 9, 2025)
            ('America/New_York', datetime(2025, 3, 8, 23, 0, 0)),  # Before DST
            ('America/New_York', datetime(2025, 3, 9, 3, 0, 0)),   # After DST
            # DST ends: first Sunday in November (November 2, 2025)
            ('America/New_York', datetime(2025, 11, 1, 23, 0, 0)),  # Before DST ends
            ('America/New_York', datetime(2025, 11, 2, 3, 0, 0)),  # After DST ends
        ]

        for tz_name, test_datetime in dst_test_cases:
            with patch('models.Settings.get_settings') as mock_settings:
                mock_settings.return_value.timezone_name = tz_name

                # Create visit
                utc_datetime = from_local_timezone(test_datetime)
                visit = PhysicianVisit(
                    physician_id=self.sample_physician.id,
                    visit_date=utc_datetime,
                    notes=f"DST test {tz_name} {test_datetime}"
                )
                self.db.session.add(visit)
                self.db.session.commit()

                # Verify round-trip conversion
                retrieved_visit = self.db.session.get(PhysicianVisit, visit.id)
                local_datetime = to_local_timezone(retrieved_visit.visit_date)

                # Allow for small differences due to DST transitions
                # Handle comparison when local_datetime is timezone-aware
                if hasattr(local_datetime, 'tzinfo') and local_datetime.tzinfo:
                    # Convert test_datetime to be timezone-aware in the same timezone
                    from pytz import timezone as pytz_timezone
                    tz = pytz_timezone(tz_name)
                    aware_test_datetime = tz.localize(test_datetime)
                    time_diff = abs((local_datetime - aware_test_datetime).total_seconds())
                else:
                    time_diff = abs((local_datetime - test_datetime).total_seconds())

                assert time_diff < 3600, \
                    f"Large time difference for {tz_name} DST test: {time_diff} seconds"

                # Test date formatting (should preserve the date)
                formatted_date = format_date(retrieved_visit.visit_date)
                expected_date = test_datetime.strftime('%d.%m.%Y')
                assert formatted_date == expected_date, \
                    f"DST date format mismatch for {tz_name}: got {formatted_date}, expected {expected_date}"

                # Clean up
                self.db.session.delete(visit)
                self.db.session.commit()

    def test_visit_form_submission(self):
        """Test that visit form submissions handle timezones correctly."""
        test_cases = [
            ('UTC', '2025-06-23'),
            ('Europe/Berlin', '2025-06-23'),     # Should not become 2025-06-22
            ('America/New_York', '2025-06-23'),  # Should not become 2025-06-24
            ('Asia/Tokyo', '2025-06-23'),        # Should not become 2025-06-22
        ]

        for tz_name, input_date in test_cases:
            with patch('models.Settings.get_settings') as mock_settings:
                mock_settings.return_value.timezone_name = tz_name

                # Submit form data
                with self.app.test_client() as client:
                    response = client.post('/physician_visits/new', data={
                        'visit_date': input_date,
                        'physician_id': self.sample_physician.id,
                        'notes': f'Test visit for {tz_name}'
                    })

                    # Should redirect on success
                    assert response.status_code == 302

                # Check the created visit
                visit = self.db.session.query(PhysicianVisit).filter_by(physician_id=self.sample_physician.id).first()
                assert visit is not None

                # Verify the date is stored correctly
                local_date = to_local_timezone(visit.visit_date)
                expected_date = datetime.strptime(input_date, '%Y-%m-%d').date()
                assert local_date.date() == expected_date, \
                    f"Visit date mismatch for {tz_name}: got {local_date.date()}, expected {expected_date}"

                # Clean up
                self.db.session.delete(visit)
                self.db.session.commit()

    def test_template_date_formatting(self):
        """Test that dates are formatted correctly in templates across timezones."""
        test_datetime = datetime(2025, 6, 23, 14, 30, 0, tzinfo=timezone.utc)

        timezones = ['UTC', 'Europe/Berlin', 'America/New_York', 'Asia/Tokyo']

        for tz_name in timezones:
            with patch('models.Settings.get_settings') as mock_settings:
                mock_settings.return_value.timezone_name = tz_name

                # Test format_date function
                formatted_date = format_date(test_datetime)
                local_dt = to_local_timezone(test_datetime)
                expected_date = local_dt.strftime('%d.%m.%Y')
                assert formatted_date == expected_date, \
                    f"format_date mismatch for {tz_name}: got {formatted_date}, expected {expected_date}"

                # Test format_datetime function
                formatted_datetime = format_datetime(test_datetime)
                expected_datetime = local_dt.strftime('%d.%m.%Y %H:%M')
                assert formatted_datetime == expected_datetime, \
                    f"format_datetime mismatch for {tz_name}: got {formatted_datetime}, expected {expected_datetime}"

    def test_medication_timestamps(self):
        """Test that medication timestamps are handled correctly."""
        test_timezones = ['UTC', 'Europe/Berlin', 'America/New_York']

        for tz_name in test_timezones:
            with patch('models.Settings.get_settings') as mock_settings:
                mock_settings.return_value.timezone_name = tz_name

                # Create medication
                medication = Medication(
                    name=f"Test Med {tz_name}",
                    physician_id=self.sample_physician.id,
                    dosage=1.0,
                    frequency=1.0,
                    is_otc=False
                )
                self.db.session.add(medication)
                self.db.session.commit()

                # Test created_at and updated_at formatting
                created_formatted = format_datetime(medication.created_at)
                updated_formatted = format_datetime(medication.updated_at)

                # Both should be valid date strings
                assert len(created_formatted.split('.')) == 3, \
                    f"Invalid created_at format for {tz_name}: {created_formatted}"
                assert len(updated_formatted.split('.')) == 3, \
                    f"Invalid updated_at format for {tz_name}: {updated_formatted}"

                # Clean up
                self.db.session.delete(medication)
                self.db.session.commit()

    def test_edge_cases(self):
        """Test edge cases like midnight, noon, and timezone boundaries."""
        edge_cases = [
            datetime(2025, 6, 23, 0, 0, 0),      # Midnight
            datetime(2025, 6, 23, 12, 0, 0),     # Noon
            datetime(2025, 6, 23, 23, 59, 59),   # Just before midnight
            datetime(2025, 12, 31, 23, 59, 59),  # Year boundary
            datetime(2025, 2, 28, 23, 59, 59),   # Month boundary (non-leap year)
        ]

        for test_dt in edge_cases:
            for tz_name in ['Europe/Berlin', 'America/New_York', 'Asia/Tokyo']:
                with patch('models.Settings.get_settings') as mock_settings:
                    mock_settings.return_value.timezone_name = tz_name

                    # Convert to UTC for storage
                    utc_dt = from_local_timezone(test_dt)

                    # Create visit
                    visit = PhysicianVisit(
                        physician_id=self.sample_physician.id,
                        visit_date=utc_dt,
                        notes=f"Edge case test {tz_name}"
                    )
                    self.db.session.add(visit)
                    self.db.session.commit()

                    # Verify round-trip conversion preserves the date
                    retrieved_visit = self.db.session.get(PhysicianVisit, visit.id)
                    local_dt = to_local_timezone(retrieved_visit.visit_date)

                    assert local_dt.date() == test_dt.date(), \
                        f"Edge case date mismatch for {tz_name} at {test_dt}: got {local_dt.date()}, expected {test_dt.date()}"

                    # Clean up
                    self.db.session.delete(visit)
                    self.db.session.commit()
