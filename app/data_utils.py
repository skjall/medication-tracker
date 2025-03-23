"""
Data export/import utilities for the Medication Tracker application.
These functions handle CSV export/import and database operations.
"""

import os
import csv
import shutil
from io import StringIO
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from flask import Response, current_app
from sqlalchemy import text

from models import db
from utils import format_date, format_datetime, ensure_timezone_utc


def export_medications_to_csv() -> Response:
    """
    Export all medications to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    from models import Medication

    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "ID",
            "Name",
            "Dosage",
            "Frequency",
            "Daily Usage",
            "Package Size N1",
            "Package Size N2",
            "Package Size N3",
            "Min Threshold",
            "Safety Margin Days",
            "Current Inventory",
            "Days Remaining",
            "Created At",
            "Updated At",
        ]
    )

    # Write data
    medications = Medication.query.all()
    for med in medications:
        writer.writerow(
            [
                med.id,
                med.name,
                med.dosage,
                med.frequency,
                med.daily_usage,
                med.package_size_n1 or "",
                med.package_size_n2 or "",
                med.package_size_n3 or "",
                med.min_threshold,
                med.safety_margin_days,
                med.inventory.current_count if med.inventory else 0,
                round(med.days_remaining, 1) if med.days_remaining else "N/A",
                format_datetime(med.created_at),
                format_datetime(med.updated_at),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=medications.csv"},
    )

    return response


def export_inventory_to_csv() -> Response:
    """
    Export current inventory to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    from models import Inventory

    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Medication ID",
            "Medication Name",
            "Current Count",
            "Packages N1",
            "Packages N2",
            "Packages N3",
            "Days Remaining",
            "Depletion Date",
            "Last Updated",
        ]
    )

    # Write data
    inventories = Inventory.query.all()
    for inv in inventories:
        depletion_date = inv.medication.depletion_date
        writer.writerow(
            [
                inv.medication_id,
                inv.medication.name,
                inv.current_count,
                inv.packages_n1,
                inv.packages_n2,
                inv.packages_n3,
                (
                    round(inv.medication.days_remaining, 1)
                    if inv.medication.days_remaining
                    else "N/A"
                ),
                format_date(depletion_date) if depletion_date else "N/A",
                format_datetime(inv.last_updated),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inventory.csv"},
    )

    return response


def export_orders_to_csv() -> Response:
    """
    Export all orders to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    from models import Order

    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Order ID",
            "Visit Date",
            "Status",
            "Created Date",
            "Medication",
            "Quantity Needed",
            "Packages N1",
            "Packages N2",
            "Packages N3",
        ]
    )

    # Write data
    orders = Order.query.all()
    for order in orders:
        for item in order.order_items:
            writer.writerow(
                [
                    order.id,
                    format_date(order.hospital_visit.visit_date),
                    order.status,
                    format_datetime(order.created_date),
                    item.medication.name,
                    item.quantity_needed,
                    item.packages_n1,
                    item.packages_n2,
                    item.packages_n3,
                ]
            )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=orders.csv"},
    )

    return response


def export_visits_to_csv() -> Response:
    """
    Export all hospital visits to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    from models import HospitalVisit
    from utils import calculate_days_until

    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Visit ID",
            "Visit Date",
            "Days Until",
            "Notes",
            "Order For Next-But-One",
            "Created At",
            "Updated At",
        ]
    )

    # Write data
    visits = HospitalVisit.query.order_by(HospitalVisit.visit_date).all()
    now = datetime.now(timezone.utc)
    for visit in visits:
        visit_date = ensure_timezone_utc(visit.visit_date)
        days_until = calculate_days_until(visit_date)

        writer.writerow(
            [
                visit.id,
                format_date(visit.visit_date),
                days_until if visit_date >= now else "Past visit",
                visit.notes or "",
                "Yes" if visit.order_for_next_but_one else "No",
                format_datetime(visit.created_at),
                format_datetime(visit.updated_at),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=hospital_visits.csv"},
    )

    return response


def create_database_backup() -> str:
    """
    Create a backup of the SQLite database file.

    Returns:
        Path to the backup file
    """
    # Get the database path from app config
    db_path = os.path.join(current_app.root_path, "data", "medication_tracker.db")

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(current_app.root_path, "data", "backups")

    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f"medication_tracker_backup_{timestamp}.db")

    # Create backup
    shutil.copy2(db_path, backup_path)

    return backup_path


def import_medications_from_csv(file_path: str) -> Tuple[int, List[str]]:
    """
    Import medications from a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        Tuple of (number of records imported, list of error messages)
    """
    from models import Medication, Inventory

    success_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Check if medication with same name exists
                    existing_med = Medication.query.filter_by(name=row["Name"]).first()

                    if existing_med:
                        errors.append(
                            f"Medication '{row['Name']}' already exists (ID: {existing_med.id})"
                        )
                        continue

                    # Create new medication
                    med = Medication(
                        name=row["Name"],
                        dosage=float(row["Dosage"]) if row["Dosage"] else 1.0,
                        frequency=float(row["Frequency"]) if row["Frequency"] else 1.0,
                        notes=row.get("Notes", ""),
                        package_size_n1=(
                            int(row["Package Size N1"])
                            if row.get("Package Size N1")
                            else None
                        ),
                        package_size_n2=(
                            int(row["Package Size N2"])
                            if row.get("Package Size N2")
                            else None
                        ),
                        package_size_n3=(
                            int(row["Package Size N3"])
                            if row.get("Package Size N3")
                            else None
                        ),
                        min_threshold=(
                            int(row["Min Threshold"]) if row.get("Min Threshold") else 0
                        ),
                        safety_margin_days=(
                            int(row["Safety Margin Days"])
                            if row.get("Safety Margin Days")
                            else 14
                        ),
                    )

                    db.session.add(med)
                    db.session.flush()  # Get the ID without committing

                    # Create inventory record
                    inventory = Inventory(
                        medication_id=med.id,
                        current_count=(
                            int(row["Current Inventory"])
                            if row.get("Current Inventory")
                            else 0
                        ),
                    )

                    db.session.add(inventory)
                    success_count += 1

                except Exception as e:
                    errors.append(
                        f"Error importing '{row.get('Name', 'unknown')}': {str(e)}"
                    )

            # Commit all changes
            if success_count > 0:
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        errors.append(f"Global import error: {str(e)}")

    return success_count, errors


def optimize_database() -> Tuple[bool, str]:
    """
    Optimize the SQLite database.

    Returns:
        Tuple of (success boolean, message)
    """
    import sqlite3

    db_path = os.path.join(current_app.root_path, "data", "medication_tracker.db")

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute VACUUM to rebuild the database file
        cursor.execute("VACUUM")

        # Execute ANALYZE to update statistics
        cursor.execute("ANALYZE")

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]

        conn.close()

        if integrity_result == "ok":
            return True, "Database optimized successfully"
        else:
            return (
                False,
                f"Database optimization completed but integrity check returned: {integrity_result}",
            )

    except Exception as e:
        return False, f"Error optimizing database: {str(e)}"


def clear_old_inventory_logs(days: int = 90) -> int:
    """
    Remove inventory logs older than the specified number of days.

    Args:
        days: Number of days to keep logs for (default: 90)

    Returns:
        Number of logs deleted
    """
    from models import InventoryLog
    from datetime import datetime, timedelta, timezone

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Delete old logs
    result = InventoryLog.query.filter(InventoryLog.timestamp < cutoff_date).delete()

    # Commit changes
    db.session.commit()

    return result
