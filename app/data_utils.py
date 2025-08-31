"""
Data export/import utilities for the Medication Tracker application.
These functions handle CSV export/import and database operations.
"""

# Standard library imports
import csv
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from io import StringIO
from typing import List, Tuple

# Third-party imports
from flask import Response, current_app
from sqlalchemy import func

# Local application imports
from models import (
    PhysicianVisit,
    Physician,
    Inventory,
    Medication,
    MedicationSchedule,
    Order,
    OrderItem,
    ScheduleType,
    db,
)
from utils import ensure_timezone_utc, format_date, format_datetime, from_local_timezone, get_data_directory


# Get a logger specific to this module
logger = logging.getLogger(__name__)


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
            "Physician ID",
            "Physician Name",
            "Is OTC",
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

    # Write data - order by ID to maintain consistent foreign key relationships
    medications = Medication.query.order_by(Medication.id).all()
    for med in medications:
        writer.writerow(
            [
                med.id,
                med.name,
                med.physician_id or "",
                med.physician.name if med.physician else "",
                "Yes" if med.is_otc else "No",
                med.dosage,
                med.frequency,
                med.daily_usage,
                med.package_size_n1 or "",
                med.package_size_n2 or "",
                med.package_size_n3 or "",
                med.min_threshold,
                med.safety_margin_days,
                med.total_inventory_count,
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

    # Write data - order by medication_id to maintain consistent foreign key relationships
    inventories = Inventory.query.order_by(Inventory.medication_id).all()
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

    # Write data - order by ID to maintain consistent foreign key relationships
    orders = Order.query.order_by(Order.id).all()
    for order in orders:
        for item in order.order_items:
            writer.writerow(
                [
                    order.id,
                    format_date(order.physician_visit.visit_date),
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


def export_physicians_to_csv() -> Response:
    """
    Export all physicians to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Physician ID",
            "Name",
            "Specialty",
            "Phone",
            "Email",
            "Address",
            "Notes",
            "Created At",
            "Updated At",
        ]
    )

    # Write data - order by ID to maintain consistent foreign key relationships
    physicians = Physician.query.order_by(Physician.id).all()
    for physician in physicians:
        writer.writerow(
            [
                physician.id,
                physician.name,
                physician.specialty or "",
                physician.phone or "",
                physician.email or "",
                physician.address or "",
                physician.notes or "",
                format_datetime(physician.created_at),
                format_datetime(physician.updated_at),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=physicians.csv"},
    )

    return response


def export_visits_to_csv() -> Response:
    """
    Export all physician visits to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    from models import PhysicianVisit
    from utils import calculate_days_until

    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Visit ID",
            "Physician ID",
            "Physician Name",
            "Visit Date",
            "Days Until",
            "Notes",
            "Order For Next-But-One",
            "Created At",
            "Updated At",
        ]
    )

    # Write data
    visits = PhysicianVisit.query.order_by(PhysicianVisit.visit_date).all()
    now = datetime.now(timezone.utc)
    for visit in visits:
        visit_date = ensure_timezone_utc(visit.visit_date)
        days_until = calculate_days_until(visit_date)

        writer.writerow(
            [
                visit.id,
                visit.physician_id or "",
                visit.physician.name if visit.physician else "",
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
        headers={"Content-disposition": "attachment; filename=physician_visits.csv"},
    )

    return response


def create_database_backup() -> str:
    """
    Create a backup of the SQLite database file.

    Returns:
        Path to the backup file
    """
    # Get the database path from app config
    db_path = os.path.join(get_data_directory(), "medication_tracker.db")

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(get_data_directory(), "backups")

    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f"medication_tracker_backup_{timestamp}.db")

    # Create backup
    shutil.copy2(db_path, backup_path)

    return backup_path


def import_medications_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import medications from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, update existing medications with the same name

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
                    medication_id = row.get("ID")
                    existing_med = None
                    
                    # First, try to find by ID if provided
                    if medication_id and medication_id.strip():
                        try:
                            existing_med = Medication.query.get(int(medication_id))
                        except (ValueError, TypeError):
                            errors.append(f"Invalid medication ID '{medication_id}' for {row['Name']}")
                            continue
                    
                    # If not found by ID, try by name
                    if not existing_med:
                        existing_med = Medication.query.filter_by(name=row["Name"]).first()

                    if existing_med and not override:
                        # If medication exists and we're not overriding, check ID consistency
                        if medication_id and str(existing_med.id) != str(medication_id):
                            errors.append(
                                f"Medication '{row['Name']}' exists with different ID (existing: {existing_med.id}, CSV: {medication_id})"
                            )
                        continue

                    # Handle physician reference with backward compatibility
                    physician_id = None
                    is_otc = False

                    # Try to get physician info - backward compatible
                    if "Physician ID" in row and row["Physician ID"]:
                        physician_id = int(row["Physician ID"])
                    elif "Physician Name" in row and row["Physician Name"]:
                        physician = Physician.query.filter_by(name=row["Physician Name"]).first()
                        if physician:
                            physician_id = physician.id

                    # Handle OTC flag - backward compatible
                    if "Is OTC" in row:
                        is_otc = row.get("Is OTC", "").lower() in ["yes", "true", "1"]

                    # Update existing medication if override is True
                    if existing_med and override:
                        med = existing_med
                        # Update fields but keep the ID
                        med.name = row["Name"]
                        med.physician_id = physician_id
                        med.is_otc = is_otc
                        med.dosage = float(row["Dosage"]) if row.get("Dosage") else 1.0
                        med.frequency = (
                            float(row["Frequency"]) if row.get("Frequency") else 1.0
                        )
                        med.notes = row.get("Notes", "")
                        med.package_size_n1 = (
                            int(row["Package Size N1"])
                            if row.get("Package Size N1")
                            else None
                        )
                        med.package_size_n2 = (
                            int(row["Package Size N2"])
                            if row.get("Package Size N2")
                            else None
                        )
                        med.package_size_n3 = (
                            int(row["Package Size N3"])
                            if row.get("Package Size N3")
                            else None
                        )
                        med.min_threshold = (
                            int(row["Min Threshold"]) if row.get("Min Threshold") else 0
                        )
                        med.safety_margin_days = (
                            int(row["Safety Margin Days"])
                            if row.get("Safety Margin Days")
                            else 30
                        )
                    else:
                        # Create new medication with specified ID if provided
                        med = Medication(
                            name=row["Name"],
                            physician_id=physician_id,
                            is_otc=is_otc,
                            dosage=float(row["Dosage"]) if row.get("Dosage") else 1.0,
                            frequency=(
                                float(row["Frequency"]) if row.get("Frequency") else 1.0
                            ),
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
                                int(row["Min Threshold"])
                                if row.get("Min Threshold")
                                else 0
                            ),
                            safety_margin_days=(
                                int(row["Safety Margin Days"])
                                if row.get("Safety Margin Days")
                                else 30
                            ),
                        )
                        
                        # Set the ID if provided in CSV
                        if medication_id and medication_id.strip():
                            try:
                                med.id = int(medication_id)
                            except (ValueError, TypeError):
                                errors.append(f"Invalid medication ID '{medication_id}' for {row['Name']}")
                                continue
                        
                        db.session.add(med)
                        db.session.flush()  # Get the ID without committing

                    # Create or update inventory record
                    inventory = Inventory.query.filter_by(medication_id=med.id).first()
                    if not inventory:
                        inventory = Inventory(
                            medication_id=med.id,
                            current_count=0,
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

    db_path = os.path.join(get_data_directory(), "medication_tracker.db")

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


def import_inventory_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import inventory data from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, overwrite existing inventory records

    Returns:
        Tuple of (number of records imported/updated, list of error messages)
    """
    success_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Check if medication exists
                    med_id = row.get("Medication ID")
                    med_name = row.get("Medication Name")

                    if med_id:
                        medication = Medication.query.get(med_id)
                    elif med_name:
                        medication = Medication.query.filter_by(name=med_name).first()
                    else:
                        errors.append(f"Row without medication ID or name: {row}")
                        continue

                    if not medication:
                        errors.append(
                            f"Medication not found: ID={med_id}, Name={med_name}"
                        )
                        continue

                    # Check if inventory exists
                    inventory = Inventory.query.filter_by(
                        medication_id=medication.id
                    ).first()

                    if inventory and not override:
                        errors.append(
                            f"Inventory for '{medication.name}' already exists. Use override to update."
                        )
                        continue

                    # Create or update inventory
                    if not inventory:
                        inventory = Inventory(medication_id=medication.id)
                        db.session.add(inventory)

                    # Update fields
                    inventory.current_count = int(row.get("Current Count", 0) or 0)
                    inventory.packages_n1 = int(row.get("Packages N1", 0) or 0)
                    inventory.packages_n2 = int(row.get("Packages N2", 0) or 0)
                    inventory.packages_n3 = int(row.get("Packages N3", 0) or 0)

                    # Parse last updated if available
                    last_updated_str = row.get("Last Updated")
                    if last_updated_str:
                        try:
                            # Try to parse datetime in various formats
                            formats = [
                                "%d.%m.%Y %H:%M",  # 01.02.2023 15:30
                                "%Y-%m-%d %H:%M:%S",  # 2023-02-01 15:30:00
                                "%Y-%m-%d",  # 2023-02-01
                            ]

                            for fmt in formats:
                                try:
                                    dt = datetime.strptime(last_updated_str, fmt)
                                    inventory.last_updated = from_local_timezone(dt)
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            logger.warning(
                                f"Could not parse date '{last_updated_str}': {e}"
                            )

                    success_count += 1

                except Exception as e:
                    errors.append(
                        f"Error importing inventory for '{row.get('Medication Name', 'unknown')}': {str(e)}"
                    )

            # Commit all changes
            if success_count > 0:
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        errors.append(f"Global import error: {str(e)}")

    return success_count, errors


def import_physicians_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import physicians from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, update existing physicians with the same name

    Returns:
        Tuple of (number of records imported/updated, list of error messages)
    """
    success_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    physician_id = row.get("Physician ID")
                    existing_physician = None
                    
                    # First, try to find by ID if provided
                    if physician_id and physician_id.strip():
                        try:
                            existing_physician = Physician.query.get(int(physician_id))
                        except (ValueError, TypeError):
                            errors.append(f"Invalid physician ID '{physician_id}' for {row['Name']}")
                            continue
                    
                    # If not found by ID, try by name
                    if not existing_physician:
                        existing_physician = Physician.query.filter_by(name=row["Name"]).first()

                    if existing_physician and not override:
                        # If physician exists and we're not overriding, skip
                        if physician_id and str(existing_physician.id) != str(physician_id):
                            errors.append(
                                f"Physician '{row['Name']}' exists with different ID (existing: {existing_physician.id}, CSV: {physician_id})"
                            )
                        continue

                    # Update existing physician if override is True
                    if existing_physician and override:
                        physician = existing_physician
                        # Update fields but keep the ID
                        physician.name = row["Name"]
                        physician.specialty = row.get("Specialty", "")
                        physician.phone = row.get("Phone", "")
                        physician.email = row.get("Email", "")
                        physician.address = row.get("Address", "")
                        physician.notes = row.get("Notes", "")
                    else:
                        # Create new physician with specified ID if provided
                        physician = Physician(
                            name=row["Name"],
                            specialty=row.get("Specialty", ""),
                            phone=row.get("Phone", ""),
                            email=row.get("Email", ""),
                            address=row.get("Address", ""),
                            notes=row.get("Notes", ""),
                        )
                        
                        # Set the ID if provided in CSV
                        if physician_id and physician_id.strip():
                            try:
                                physician.id = int(physician_id)
                            except (ValueError, TypeError):
                                errors.append(f"Invalid physician ID '{physician_id}' for {row['Name']}")
                                continue
                        
                        db.session.add(physician)

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


def import_visits_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import physician visits from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, update existing visits with the same date

    Returns:
        Tuple of (number of records imported/updated, list of error messages)
    """

    success_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    visit_id = row.get("Visit ID")
                    existing_visit = None
                    
                    # First, try to find by ID if provided
                    if visit_id and visit_id.strip():
                        try:
                            existing_visit = PhysicianVisit.query.get(int(visit_id))
                        except (ValueError, TypeError):
                            errors.append(f"Invalid visit ID '{visit_id}' for visit on {row.get('Visit Date', 'unknown date')}")
                            continue
                    
                    # Parse visit date
                    visit_date_str = row.get("Visit Date")
                    if not visit_date_str:
                        errors.append(f"Missing visit date in row: {row}")
                        continue

                    # Try to parse date in various formats
                    visit_date = None
                    formats = [
                        "%d.%m.%Y",  # 01.02.2023
                        "%Y-%m-%d",  # 2023-02-01
                    ]

                    for fmt in formats:
                        try:
                            dt = datetime.strptime(visit_date_str, fmt)
                            visit_date = from_local_timezone(dt)
                            break
                        except ValueError:
                            continue

                    if not visit_date:
                        errors.append(f"Could not parse visit date: {visit_date_str}")
                        continue

                    # Handle physician reference with backward compatibility
                    physician_id = None
                    if "Physician ID" in row and row["Physician ID"]:
                        physician_id = int(row["Physician ID"])
                    elif "Physician Name" in row and row["Physician Name"]:
                        physician = Physician.query.filter_by(name=row["Physician Name"]).first()
                        if physician:
                            physician_id = physician.id

                    # If not found by ID, check if visit exists with same date
                    if not existing_visit:
                        existing_visit = PhysicianVisit.query.filter(
                            func.date(PhysicianVisit.visit_date) == func.date(visit_date)
                        ).first()

                    if existing_visit and not override:
                        # If visit exists and we're not overriding, check ID consistency
                        if visit_id and str(existing_visit.id) != str(visit_id):
                            errors.append(
                                f"Visit on {visit_date_str} exists with different ID (existing: {existing_visit.id}, CSV: {visit_id})"
                            )
                        continue

                    # Create or update visit
                    if existing_visit and override:
                        visit = existing_visit
                        # Update fields but keep the ID
                        visit.visit_date = visit_date
                        visit.physician_id = physician_id
                    else:
                        # Create new visit with specified ID if provided
                        visit = PhysicianVisit(visit_date=visit_date, physician_id=physician_id)
                        
                        # Set the ID if provided in CSV
                        if visit_id and visit_id.strip():
                            try:
                                visit.id = int(visit_id)
                            except (ValueError, TypeError):
                                errors.append(f"Invalid visit ID '{visit_id}' for visit on {visit_date_str}")
                                continue
                        
                        db.session.add(visit)

                    # Update fields
                    visit.notes = row.get("Notes", "")
                    visit.order_for_next_but_one = row.get(
                        "Order For Next-But-One", ""
                    ).lower() in ["yes", "true", "1"]

                    success_count += 1

                except Exception as e:
                    errors.append(
                        f"Error importing visit on '{row.get('Visit Date', 'unknown')}': {str(e)}"
                    )

            # Commit all changes
            if success_count > 0:
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        errors.append(f"Global import error: {str(e)}")

    return success_count, errors


def import_orders_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import orders from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, update existing orders with the same ID or create new ones

    Returns:
        Tuple of (number of records imported/updated, list of error messages)
    """
    success_count = 0
    errors = []

    # Keep track of processed orders to handle multiple items per order
    processed_orders = {}

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Get order ID and visit date
                    order_id = row.get("Order ID")
                    visit_date_str = row.get("Visit Date")

                    if not visit_date_str:
                        errors.append(f"Missing visit date in row: {row}")
                        continue

                    # Parse visit date
                    visit_date = None
                    formats = [
                        "%d.%m.%Y",  # 01.02.2023
                        "%Y-%m-%d",  # 2023-02-01
                    ]

                    for fmt in formats:
                        try:
                            dt = datetime.strptime(visit_date_str, fmt)
                            visit_date = from_local_timezone(dt)
                            break
                        except ValueError:
                            continue

                    if not visit_date:
                        errors.append(f"Could not parse visit date: {visit_date_str}")
                        continue

                    # Find corresponding physician visit
                    visit = PhysicianVisit.query.filter(
                        func.date(PhysicianVisit.visit_date) == func.date(visit_date)
                    ).first()

                    if not visit:
                        # Create the visit if it doesn't exist
                        visit = PhysicianVisit(visit_date=visit_date)
                        db.session.add(visit)
                        db.session.flush()  # Get ID without committing

                    # Check if we've seen this order before in the current import
                    if order_id in processed_orders:
                        order = processed_orders[order_id]
                    else:
                        # Check if order exists
                        existing_order = None
                        if order_id and order_id.strip():
                            try:
                                existing_order = Order.query.get(int(order_id))
                            except (ValueError, TypeError):
                                errors.append(f"Invalid order ID '{order_id}' for order")
                                continue

                        if existing_order and not override:
                            errors.append(
                                f"Order #{order_id} already exists. Use override to update."
                            )
                            continue

                        if existing_order and override:
                            order = existing_order
                            # Update visit reference in case it changed
                            order.physician_visit_id = visit.id
                        else:
                            # Create new order with specified ID if provided
                            order = Order(physician_visit_id=visit.id)
                            
                            # Set the ID if provided in CSV
                            if order_id and order_id.strip():
                                try:
                                    order.id = int(order_id)
                                except (ValueError, TypeError):
                                    errors.append(f"Invalid order ID '{order_id}' for order")
                                    continue
                            
                            db.session.add(order)

                        # Update order fields
                        order.status = row.get("Status", "planned")

                        # Parse created date if available
                        created_date_str = row.get("Created Date")
                        if created_date_str:
                            try:
                                formats = [
                                    "%d.%m.%Y %H:%M",
                                    "%Y-%m-%d %H:%M:%S",
                                    "%Y-%m-%d",
                                ]
                                for fmt in formats:
                                    try:
                                        dt = datetime.strptime(created_date_str, fmt)
                                        order.created_date = from_local_timezone(dt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass  # Use default date if parsing fails

                        processed_orders[order_id] = order

                    # Process medication item
                    med_name = row.get("Medication")
                    if not med_name:
                        continue  # Skip if no medication specified

                    medication = Medication.query.filter_by(name=med_name).first()
                    if not medication:
                        errors.append(f"Medication not found: {med_name}")
                        continue

                    # Check if item already exists
                    existing_item = None
                    for item in order.order_items:
                        if item.medication_id == medication.id:
                            existing_item = item
                            break

                    if existing_item:
                        item = existing_item
                    else:
                        item = OrderItem(order=order, medication_id=medication.id)
                        db.session.add(item)
                        order.order_items.append(item)

                    # Update item fields
                    item.quantity_needed = int(row.get("Quantity Needed", 0) or 0)
                    item.packages_n1 = int(row.get("Packages N1", 0) or 0)
                    item.packages_n2 = int(row.get("Packages N2", 0) or 0)
                    item.packages_n3 = int(row.get("Packages N3", 0) or 0)

                    success_count += 1

                except Exception as e:
                    errors.append(f"Error importing order item: {str(e)}")

            # Commit all changes
            if success_count > 0:
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        errors.append(f"Global import error: {str(e)}")

    return success_count, errors


def reset_inventory_data() -> int:
    """
    Reset inventory data by deleting all inventory records.

    Returns:
        Number of records deleted
    """
    try:
        # Delete inventory logs first
        from models import InventoryLog

        InventoryLog.query.delete()

        # Delete inventory records
        count = Inventory.query.delete()

        db.session.commit()

        # Recreate empty inventory for each medication
        medications = Medication.query.all()
        for med in medications:
            inventory = Inventory(medication_id=med.id, current_count=0)
            db.session.add(inventory)

        db.session.commit()

        return count
    except Exception as e:
        db.session.rollback()
        raise e


def reset_visits_data() -> int:
    """
    Reset physician visit data by deleting all visit records.

    Returns:
        Number of records deleted
    """
    try:
        # Delete orders first (they depend on visits)
        reset_orders_data()

        # Delete visits
        count = PhysicianVisit.query.delete()
        db.session.commit()

        return count
    except Exception as e:
        db.session.rollback()
        raise e


def reset_orders_data() -> int:
    """
    Reset order data by deleting all order records.

    Returns:
        Number of records deleted
    """
    try:
        # Delete order items first
        OrderItem.query.delete()

        # Delete orders
        count = Order.query.delete()
        db.session.commit()

        return count
    except Exception as e:
        db.session.rollback()
        raise e


def export_schedules_to_csv() -> Response:
    """
    Export all medication schedules to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Schedule ID",
            "Medication ID",
            "Medication Name",
            "Schedule Type",
            "Interval Days",
            "Weekdays",
            "Times of Day",
            "Units Per Dose",
            "Last Deduction",
            "Created At",
            "Updated At",
        ]
    )

    # Write data - order by ID to maintain consistent foreign key relationships
    schedules = MedicationSchedule.query.order_by(MedicationSchedule.id).all()
    for schedule in schedules:
        writer.writerow(
            [
                schedule.id,
                schedule.medication_id,
                schedule.medication.name,
                schedule.schedule_type.value,
                schedule.interval_days,
                (
                    ",".join(map(str, schedule.formatted_weekdays))
                    if schedule.formatted_weekdays
                    else ""
                ),
                ",".join(schedule.formatted_times),
                schedule.units_per_dose,
                (
                    format_datetime(schedule.last_deduction)
                    if schedule.last_deduction
                    else ""
                ),
                format_datetime(schedule.created_at),
                format_datetime(schedule.updated_at),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-disposition": "attachment; filename=schedules.csv"
        },
    )

    return response


def import_schedules_from_csv(
    file_path: str, override: bool = False
) -> Tuple[int, List[str]]:
    """
    Import medication schedules from a CSV file.

    Args:
        file_path: Path to the CSV file
        override: If True, update existing schedules with the same ID or create new ones

    Returns:
        Tuple of (number of records imported/updated, list of error messages)
    """
    success_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Check if medication exists
                    med_id = row.get("Medication ID")
                    med_name = row.get("Medication Name")

                    if med_id:
                        medication = Medication.query.get(med_id)
                    elif med_name:
                        medication = Medication.query.filter_by(name=med_name).first()
                    else:
                        errors.append(f"Row without medication ID or name: {row}")
                        continue

                    if not medication:
                        errors.append(
                            f"Medication not found: ID={med_id}, Name={med_name}"
                        )
                        continue

                    # Check if schedule exists
                    schedule_id = row.get("Schedule ID")
                    existing_schedule = None

                    if schedule_id and schedule_id.isdigit():
                        existing_schedule = MedicationSchedule.query.get(
                            int(schedule_id)
                        )

                    if existing_schedule and not override:
                        errors.append(
                            f"Schedule #{schedule_id} already exists. Use override to update."
                        )
                        continue

                    # Create or update schedule
                    if existing_schedule and override:
                        schedule = existing_schedule
                        # Update medication_id in case it changed
                        schedule.medication_id = medication.id
                    else:
                        # Create new schedule with specified ID if provided
                        schedule = MedicationSchedule(medication_id=medication.id)
                        
                        # Set the ID if provided in CSV
                        if schedule_id and schedule_id.strip():
                            try:
                                schedule.id = int(schedule_id)
                            except (ValueError, TypeError):
                                errors.append(f"Invalid schedule ID '{schedule_id}' for medication {medication.name}")
                                continue
                        
                        db.session.add(schedule)

                    # Update schedule fields
                    schedule_type_value = row.get("Schedule Type", "daily")
                    try:
                        schedule.schedule_type = ScheduleType(schedule_type_value)
                    except ValueError:
                        errors.append(
                            f"Invalid schedule type: {schedule_type_value}. Using 'daily'."
                        )
                        schedule.schedule_type = ScheduleType.DAILY

                    # Update interval days
                    schedule.interval_days = int(row.get("Interval Days", 1) or 1)

                    # Update weekdays
                    weekdays_str = row.get("Weekdays", "")
                    if weekdays_str:
                        try:
                            weekdays = [int(day) for day in weekdays_str.split(",")]
                            schedule.weekdays = json.dumps(weekdays)
                        except Exception as e:
                            errors.append(f"Error parsing weekdays: {e}")
                            schedule.weekdays = json.dumps([])
                    else:
                        schedule.weekdays = json.dumps([])

                    # Update times of day
                    times_str = row.get("Times of Day", "")
                    if times_str:
                        times = times_str.split(",")
                        schedule.times_of_day = json.dumps(times)
                    else:
                        errors.append(
                            "No times of day specified for schedule. Using default '09:00'."
                        )
                        schedule.times_of_day = json.dumps(["09:00"])

                    # Update units per dose
                    try:
                        schedule.units_per_dose = float(
                            row.get("Units Per Dose", 1.0) or 1.0
                        )
                    except ValueError:
                        errors.append(
                            f"Invalid units per dose: {row.get('Units Per Dose')}. Using 1.0."
                        )
                        schedule.units_per_dose = 1.0

                    success_count += 1

                except Exception as e:
                    errors.append(f"Error importing schedule: {str(e)}")

            # Commit all changes
            if success_count > 0:
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        errors.append(f"Global import error: {str(e)}")

    return success_count, errors


def reset_physicians_data() -> int:
    """
    Reset physician data by deleting all physician records.

    Returns:
        Number of records deleted
    """
    try:
        # First clear physician references from related tables
        # Set physician_id to None for medications
        medications = Medication.query.filter(Medication.physician_id.isnot(None)).all()
        for med in medications:
            med.physician_id = None
        
        # Set physician_id to None for visits  
        visits = PhysicianVisit.query.filter(PhysicianVisit.physician_id.isnot(None)).all()
        for visit in visits:
            visit.physician_id = None
        
        # Delete physicians
        count = Physician.query.delete()
        db.session.commit()

        return count
    except Exception as e:
        db.session.rollback()
        raise e


def reset_schedules_data() -> int:
    """
    Reset schedule data by deleting all medication schedule records.

    Returns:
        Number of records deleted
    """
    try:
        # Delete schedules
        count = MedicationSchedule.query.delete()
        db.session.commit()

        return count
    except Exception as e:
        db.session.rollback()
        raise e
