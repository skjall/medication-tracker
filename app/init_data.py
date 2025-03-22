"""
Initialization script to create sample data for testing.

This module provides functions to create sample medications,
inventory records, and hospital visits for initial testing.
"""

from datetime import datetime, timedelta
from typing import List

from models import (
    db,
    Medication,
    Inventory,
    HospitalVisit,
    Order,
    OrderItem,
    InventoryLog,
)


def initialize_sample_data() -> None:
    """Initialize sample data for testing."""
    print("Initializing sample data...")

    # Create sample medications
    medications = create_sample_medications()

    # Create sample hospital visits
    visits = create_sample_visits()

    # Create sample orders
    create_sample_orders(medications, visits)

    print("Sample data initialization complete!")


def create_sample_medications() -> List[Medication]:
    """Create sample medications and their inventory records."""
    print("Creating sample medications...")

    # Define some sample medications
    medications_data = [
        {
            "name": "Lisinopril",
            "dosage": 10,
            "frequency": 1,
            "notes": "For blood pressure control",
            "package_size_n1": 30,
            "package_size_n2": 90,
            "package_size_n3": 180,
            "min_threshold": 30,
            "safety_margin_days": 14,
            "inventory": 75,
        },
        {
            "name": "Metformin",
            "dosage": 500,
            "frequency": 2,
            "notes": "For diabetes management",
            "package_size_n1": 60,
            "package_size_n2": 120,
            "package_size_n3": 0,
            "min_threshold": 50,
            "safety_margin_days": 14,
            "inventory": 95,
        },
        {
            "name": "Levothyroxine",
            "dosage": 125,
            "frequency": 1,
            "notes": "For hypothyroidism",
            "package_size_n1": 30,
            "package_size_n2": 100,
            "package_size_n3": 0,
            "min_threshold": 20,
            "safety_margin_days": 10,
            "inventory": 15,
        },
        {
            "name": "Atorvastatin",
            "dosage": 20,
            "frequency": 1,
            "notes": "For cholesterol management",
            "package_size_n1": 30,
            "package_size_n2": 90,
            "package_size_n3": 0,
            "min_threshold": 15,
            "safety_margin_days": 10,
            "inventory": 45,
        },
        {
            "name": "Amlodipine",
            "dosage": 5,
            "frequency": 1,
            "notes": "For blood pressure control",
            "package_size_n1": 30,
            "package_size_n2": 90,
            "package_size_n3": 0,
            "min_threshold": 15,
            "safety_margin_days": 7,
            "inventory": 60,
        },
    ]

    # Create medications and inventory records
    created_medications = []
    for data in medications_data:
        # Create medication
        medication = Medication(
            name=data["name"],
            dosage=data["dosage"],
            frequency=data["frequency"],
            notes=data["notes"],
            package_size_n1=data["package_size_n1"],
            package_size_n2=data["package_size_n2"],
            package_size_n3=data["package_size_n3"],
            min_threshold=data["min_threshold"],
            safety_margin_days=data["safety_margin_days"],
        )

        # Create inventory record
        inventory = Inventory(medication=medication, current_count=data["inventory"])

        # Calculate package counts based on typical distribution
        if medication.package_size_n3 > 0:
            inventory.packages_n3 = data["inventory"] // (
                3 * medication.package_size_n3
            )
            remaining = data["inventory"] - (
                inventory.packages_n3 * medication.package_size_n3
            )
        else:
            remaining = data["inventory"]

        if medication.package_size_n2 > 0:
            inventory.packages_n2 = remaining // medication.package_size_n2
            remaining -= inventory.packages_n2 * medication.package_size_n2

        if medication.package_size_n1 > 0:
            inventory.packages_n1 = remaining // medication.package_size_n1

        # Create a log entry for initial inventory
        log = InventoryLog(
            inventory=inventory,
            previous_count=0,
            adjustment=data["inventory"],
            new_count=data["inventory"],
            notes="Initial inventory",
        )

        db.session.add(medication)
        db.session.add(inventory)
        db.session.add(log)
        created_medications.append(medication)

    db.session.commit()
    print(f"Created {len(created_medications)} sample medications with inventory.")

    return created_medications


def create_sample_visits() -> List[HospitalVisit]:
    """Create sample hospital visits."""
    print("Creating sample hospital visits...")

    # Create a past visit
    past_visit = HospitalVisit(
        visit_date=datetime.utcnow() - timedelta(days=30),
        notes="Regular checkup with Dr. Smith",
    )

    # Create an upcoming visit in 14 days
    upcoming_visit = HospitalVisit(
        visit_date=datetime.utcnow() + timedelta(days=14),
        notes="Follow-up appointment with Dr. Smith",
    )

    # Create a future visit in 3 months
    future_visit = HospitalVisit(
        visit_date=datetime.utcnow() + timedelta(days=90),
        notes="Annual physical with Dr. Johnson",
    )

    db.session.add(past_visit)
    db.session.add(upcoming_visit)
    db.session.add(future_visit)
    db.session.commit()

    print("Created 3 sample hospital visits.")
    return [past_visit, upcoming_visit, future_visit]


def create_sample_orders(
    medications: List[Medication], visits: List[HospitalVisit]
) -> None:
    """Create sample orders for visits."""
    print("Creating sample orders...")

    # Create a fulfilled order for the past visit
    past_order = Order(
        hospital_visit=visits[0],
        status="fulfilled",
        created_date=datetime.utcnow() - timedelta(days=35),
    )

    # Add order items for past order
    for med in medications[:3]:
        item = OrderItem(
            order=past_order,
            medication=med,
            quantity_needed=int(med.daily_usage * 30),
        )

        # Set package quantities
        if med.package_size_n1:
            item.packages_n1 = 1
        if med.package_size_n2:
            item.packages_n2 = 0
        if med.package_size_n3:
            item.packages_n3 = 0

        db.session.add(item)

    # Create a planned order for the upcoming visit
    upcoming_order = Order(
        hospital_visit=visits[1],
        status="planned",
        created_date=datetime.utcnow() - timedelta(days=2),
    )

    # Add order items for upcoming order
    for med in medications:
        needed = int(med.daily_usage * (14 + med.safety_margin_days))
        current = med.inventory.current_count if med.inventory else 0
        additional = max(0, needed - current)

        if additional > 0:
            item = OrderItem(
                order=upcoming_order, medication=med, quantity_needed=additional
            )

            # Calculate packages
            packages = med.calculate_packages_needed(additional)
            item.packages_n1 = packages["N1"]
            item.packages_n2 = packages["N2"]
            item.packages_n3 = packages["N3"]

            db.session.add(item)

    db.session.add(past_order)
    db.session.add(upcoming_order)
    db.session.commit()

    print("Created 2 sample orders.")


if __name__ == "__main__":
    # This can be run as a standalone script
    from main import create_app

    app = create_app()
    with app.app_context():
        # First create tables if they don't exist
        db.create_all()

        # Check if we already have data
        if Medication.query.count() == 0:
            initialize_sample_data()
        else:
            print("Data already exists. Skipping initialization.")
