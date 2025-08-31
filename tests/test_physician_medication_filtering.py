"""
Tests for physician-based medication filtering in orders.

NOTE: This test file is for the legacy Medication model.
The new ActiveIngredient model doesn't have physician relationships,
so physician-based filtering is no longer applicable.
"""

# Standard library imports
from datetime import datetime, timedelta, timezone
import unittest

# Local application imports
from .test_base import BaseTestCase
from app.models import (
    Medication,
    Physician,
    PhysicianVisit,
    Order,
    OrderItem,
    Inventory,
)


class TestPhysicianMedicationFiltering(BaseTestCase):
    """Test cases for physician-based medication filtering in orders."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create two physicians
        self.physician1 = Physician(
            name="Dr. Smith",
            specialty="Cardiology"
        )
        self.physician2 = Physician(
            name="Dr. Jones",
            specialty="Endocrinology"
        )
        self.db.session.add(self.physician1)
        self.db.session.add(self.physician2)
        self.db.session.commit()

        # Create medications for physician 1
        self.med1_physician1 = Medication(
            name="Heart Med 1",
            physician_id=self.physician1.id,
            is_otc=False,
            dosage=1.0,
            frequency=2.0,
            package_size_n1=30
        )
        self.med2_physician1 = Medication(
            name="Heart Med 2",
            physician_id=self.physician1.id,
            is_otc=False,
            dosage=0.5,
            frequency=1.0,
            package_size_n1=60
        )

        # Create medications for physician 2
        self.med1_physician2 = Medication(
            name="Diabetes Med 1",
            physician_id=self.physician2.id,
            is_otc=False,
            dosage=500.0,
            frequency=2.0,
            package_size_n1=100
        )

        # Create OTC medications (no physician)
        self.med_otc1 = Medication(
            name="Vitamin D",
            physician_id=None,
            is_otc=True,
            dosage=1000.0,
            frequency=1.0,
            package_size_n1=90
        )
        self.med_otc2 = Medication(
            name="Omega-3",
            physician_id=None,
            is_otc=True,
            dosage=1000.0,
            frequency=2.0,
            package_size_n1=60
        )

        # Add all medications to database
        self.db.session.add_all([
            self.med1_physician1, self.med2_physician1,
            self.med1_physician2, self.med_otc1, self.med_otc2
        ])

        # Create inventory for all medications
        for med in [self.med1_physician1, self.med2_physician1,
                    self.med1_physician2, self.med_otc1, self.med_otc2]:
            inventory = Inventory(medication=med, current_count=50)
            self.db.session.add(inventory)

        self.db.session.commit()

        # Create visits
        visit_date = datetime.now(timezone.utc) + timedelta(days=30)

        # Visit with physician 1
        self.visit_physician1 = PhysicianVisit(
            physician_id=self.physician1.id,
            visit_date=visit_date,
            notes="Cardiology checkup"
        )

        # Visit with physician 2
        self.visit_physician2 = PhysicianVisit(
            physician_id=self.physician2.id,
            visit_date=visit_date + timedelta(days=60),
            notes="Diabetes checkup"
        )

        # Visit without physician (for OTC)
        self.visit_no_physician = PhysicianVisit(
            physician_id=None,
            visit_date=visit_date + timedelta(days=90),
            notes="Supplements refill"
        )

        self.db.session.add_all([
            self.visit_physician1, self.visit_physician2, self.visit_no_physician
        ])
        self.db.session.commit()

    @unittest.skip("Physician filtering no longer applicable with ActiveIngredient model")
    def test_order_shows_only_physician1_medications(self):
        """Test that an order for physician 1 visit only shows physician 1 medications."""
        # Simulate the filtering logic from the route
        available_meds = self.db.session.query(Medication).filter_by(
            physician_id=self.visit_physician1.physician_id
        ).all()

        # Should only contain physician 1's medications
        self.assertEqual(len(available_meds), 2)
        self.assertIn(self.med1_physician1, available_meds)
        self.assertIn(self.med2_physician1, available_meds)

        # Should not contain other medications
        self.assertNotIn(self.med1_physician2, available_meds)
        self.assertNotIn(self.med_otc1, available_meds)
        self.assertNotIn(self.med_otc2, available_meds)

    @unittest.skip("Physician filtering no longer applicable with ActiveIngredient model")
    def test_order_shows_only_physician2_medications(self):
        """Test that an order for physician 2 visit only shows physician 2 medications."""
        # Simulate the filtering logic from the route
        available_meds = self.db.session.query(Medication).filter_by(
            physician_id=self.visit_physician2.physician_id
        ).all()

        # Should only contain physician 2's medications
        self.assertEqual(len(available_meds), 1)
        self.assertIn(self.med1_physician2, available_meds)

        # Should not contain other medications
        self.assertNotIn(self.med1_physician1, available_meds)
        self.assertNotIn(self.med2_physician1, available_meds)
        self.assertNotIn(self.med_otc1, available_meds)
        self.assertNotIn(self.med_otc2, available_meds)

    @unittest.skip("Physician filtering no longer applicable with ActiveIngredient model")
    def test_order_shows_only_otc_medications_for_no_physician(self):
        """Test that an order for visit without physician only shows OTC medications."""
        # Simulate the filtering logic from the route
        available_meds = self.db.session.query(Medication).filter_by(physician_id=None).all()

        # Should only contain OTC medications
        self.assertEqual(len(available_meds), 2)
        self.assertIn(self.med_otc1, available_meds)
        self.assertIn(self.med_otc2, available_meds)

        # Should not contain physician medications
        self.assertNotIn(self.med1_physician1, available_meds)
        self.assertNotIn(self.med2_physician1, available_meds)
        self.assertNotIn(self.med1_physician2, available_meds)

    @unittest.skip("Physician filtering no longer applicable with ActiveIngredient model")
    def test_order_creation_respects_physician_filter(self):
        """Test that creating an order only allows medications from the visit's physician."""
        # Create an order for physician 1 visit
        order = Order(
            physician_visit_id=self.visit_physician1.id,
            status="planned"
        )
        self.db.session.add(order)

        # Try to add an order item for physician 1's medication (should work)
        item1 = OrderItem(
            order=order,
            medication_id=self.med1_physician1.id,
            quantity_needed=60,
            packages_n1=2,
            packages_n2=0,
            packages_n3=0
        )
        self.db.session.add(item1)
        self.db.session.commit()

        # Verify it was added
        self.assertEqual(len(order.order_items), 1)
        self.assertEqual(order.order_items[0].medication_id, self.med1_physician1.id)

    @unittest.skip("Physician filtering no longer applicable with ActiveIngredient model")
    def test_mixed_physician_visits_maintain_separation(self):
        """Test that multiple visits with different physicians maintain medication separation."""
        # Create orders for each visit type
        order1 = Order(physician_visit_id=self.visit_physician1.id, status="planned")
        order2 = Order(physician_visit_id=self.visit_physician2.id, status="planned")
        order3 = Order(physician_visit_id=self.visit_no_physician.id, status="planned")

        self.db.session.add_all([order1, order2, order3])
        self.db.session.commit()

        # Each order should only have access to its physician's medications
        # This would be enforced by the route filtering, not the model
        # So we're testing the conceptual separation here

        # Verify visits have correct physician associations
        self.assertEqual(order1.physician_visit.physician_id, self.physician1.id)
        self.assertEqual(order2.physician_visit.physician_id, self.physician2.id)
        self.assertIsNone(order3.physician_visit.physician_id)
