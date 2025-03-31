"""
Routes for managing application settings.

This file combines the functionality from:
- hospital_visit_settings.py
- advanced_settings.py

into a single unified settings module to avoid route conflicts.
"""

import os
import tempfile
import pytz
import logging
from datetime import datetime, timezone
from typing import Dict, List

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
from werkzeug.utils import secure_filename

from models import (
    db,
    Medication,
    Inventory,
    InventoryLog,
    HospitalVisit,
    HospitalVisitSettings,
    MedicationSchedule,
    Order,
    OrderItem,
)
from data_utils import (
    export_medications_to_csv,
    export_inventory_to_csv,
    export_orders_to_csv,
    export_visits_to_csv,
    export_schedules_to_csv,
    create_database_backup,
    import_medications_from_csv,
    optimize_database,
    clear_old_inventory_logs,
)

# Logger for this module
logger = logging.getLogger(__name__)

# Import timezone helper functions
try:
    # Try direct import first
    from timezone_helper import get_timezone_display_info, validate_timezone

    logger.info("Successfully imported timezone_helper")
except ImportError:
    # Fall back to relative import
    try:
        from app.timezone_helper import get_timezone_display_info, validate_timezone

        logger.info("Successfully imported timezone_helper from app package")
    except ImportError as ie:
        # Log the error
        logger.error(f"Failed to import timezone_helper: {ie}")

        # Define fallback functions
        def get_timezone_display_info() -> List[Dict[str, str]]:
            """
            Get timezone display information including region and current offset.
            Fallback implementation if timezone_helper can't be imported.
            """
            logger.warning("Using fallback implementation of get_timezone_display_info")
            now = datetime.now(timezone.utc)
            timezone_info = []

            try:
                for tz_name in sorted(pytz.common_timezones):
                    try:
                        tz = pytz.timezone(tz_name)
                        offset_seconds = tz.utcoffset(now).total_seconds()
                        offset_hours = int(offset_seconds / 3600)
                        offset_minutes = int((offset_seconds % 3600) / 60)

                        # Format: "UTC+01:00" or "UTC-08:00"
                        offset_str = f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:02d}:{abs(offset_minutes):02d}"

                        # Split timezone name into region/city
                        parts = tz_name.split("/")
                        region = parts[0] if len(parts) > 0 else ""
                        city = parts[1] if len(parts) > 1 else tz_name

                        display_name = f"{city.replace('_', ' ')} ({offset_str})"

                        timezone_info.append(
                            {
                                "name": tz_name,
                                "region": region,
                                "city": city,
                                "offset": offset_str,
                                "display_name": display_name,
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error processing timezone {tz_name}: {e}")
                        continue

                # Log the result
                logger.info(
                    f"Fallback implementation found {len(timezone_info)} timezones"
                )

                # Sort by region then offset
                return sorted(timezone_info, key=lambda x: (x["region"], x["offset"]))
            except Exception as e:
                logger.error(f"Error in get_timezone_display_info: {e}")
                return []

        def validate_timezone(timezone_name: str) -> bool:
            """
            Validate if a timezone name is valid.
            Fallback implementation if timezone_helper can't be imported.
            """
            try:
                pytz.timezone(timezone_name)
                return True
            except Exception:
                return False


# Create a single settings blueprint to combine both previous routes
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/hospital_visits", methods=["GET", "POST"])
def hospital_visits():
    """
    Display and update hospital visit settings.
    """
    logger.info("Accessing hospital visit settings page")

    # Get current settings
    settings = HospitalVisitSettings.get_settings()

    if request.method == "POST":
        # Update settings from form
        settings.default_visit_interval = int(
            request.form.get("default_visit_interval", 90)
        )
        settings.auto_schedule_visits = "auto_schedule_visits" in request.form
        settings.default_order_for_next_but_one = (
            "default_order_for_next_but_one" in request.form
        )

        db.session.commit()

        flash("Hospital visit settings updated successfully", "success")
        return redirect(url_for("settings.hospital_visits"))

    # Calculate actual average interval for information purposes
    from hospital_visit_utils import calculate_days_between_visits

    actual_interval = calculate_days_between_visits()

    return render_template(
        "settings/hospital_visits.html",
        settings=settings,
        actual_interval=actual_interval,
    )


@settings_bp.route("/update_visit_order_planning/<int:visit_id>", methods=["POST"])
def update_visit_order_planning(visit_id: int):
    """
    Update the order planning setting for a specific visit.
    """
    logger.info(f"Updating order planning for visit {visit_id}")

    visit = HospitalVisit.query.get_or_404(visit_id)

    # Toggle the setting
    visit.order_for_next_but_one = not visit.order_for_next_but_one
    db.session.commit()

    if visit.order_for_next_but_one:
        message = "Orders for this visit will now be planned to last until the next-but-one visit"
    else:
        message = "Orders for this visit will now be planned to last until the next visit only"

    flash(message, "success")
    return redirect(url_for("visits.show", id=visit_id))


@settings_bp.route("/advanced", methods=["GET"])
def advanced():
    """
    Advanced settings page (e.g., backup/restore, system settings).
    """
    logger.info("Loading advanced settings page")

    # Get hospital visit settings
    settings = HospitalVisitSettings.get_settings()

    # Get database statistics
    med_count = Medication.query.count()
    schedule_count = MedicationSchedule.query.count()
    upcoming_visits_count = HospitalVisit.query.filter(
        HospitalVisit.visit_date >= datetime.now(timezone.utc)
    ).count()

    # Get inventory logs count
    inventory_logs_count = InventoryLog.query.count()

    # Get database path for display
    db_path = os.path.join("data", "medication_tracker.db")

    # Get database size
    db_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
    db_size_mb = (
        round(os.path.getsize(db_file_path) / (1024 * 1024), 2)
        if os.path.exists(db_file_path)
        else 0
    )

    # Import timezone helper for getting timezone information
    logger.info("Getting timezone display information")
    try:
        timezone_info = get_timezone_display_info()
        logger.info(f"Got {len(timezone_info)} timezone entries")
    except Exception as e:
        logger.error(f"Error getting timezone display info: {e}")
        timezone_info = []

    return render_template(
        "settings/advanced.html",
        settings=settings,
        med_count=med_count,
        schedule_count=schedule_count,
        upcoming_visits_count=upcoming_visits_count,
        inventory_logs_count=inventory_logs_count,
        db_path=db_path,
        db_size_mb=db_size_mb,
        timezone_info=timezone_info,
    )


@settings_bp.route("/export/<data_type>")
def export_data(data_type: str):
    """
    Export various data types to CSV.

    Args:
        data_type: Type of data to export (medications, inventory, orders, visits)
    """
    logger.info(f"Exporting data type: {data_type}")

    if data_type == "medications":
        return export_medications_to_csv()
    elif data_type == "inventory":
        return export_inventory_to_csv()
    elif data_type == "orders":
        return export_orders_to_csv()
    elif data_type == "visits":
        return export_visits_to_csv()
    elif data_type == "schedules":
        return export_schedules_to_csv()
    else:
        flash(f"Unknown export type: {data_type}", "error")
        return redirect(url_for("settings.advanced"))


@settings_bp.route("/backup")
def backup_database():
    """Create and download a backup of the database."""
    logger.info("Creating database backup")

    try:
        backup_path = create_database_backup()

        # Send the file to the user
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=f"medication_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            mimetype="application/octet-stream",
        )
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        flash(f"Error creating backup: {str(e)}", "error")
        return redirect(url_for("settings.advanced"))


@settings_bp.route("/import", methods=["POST"])
def import_data():
    """Import data from uploaded CSV files."""
    logger.info("Handling data import")

    if "file" not in request.files:
        flash("No file part", "error")
        return redirect(url_for("settings.advanced"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("settings.advanced"))

    # Save the file to a temporary location
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(file_path)

    # Import based on file type selection
    import_type = request.form.get("import_type", "medications")

    if import_type == "medications":
        success_count, errors = import_medications_from_csv(file_path)

        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, "warning")
            if len(errors) > 5:
                flash(f"...and {len(errors) - 5} more errors", "warning")

        if success_count > 0:
            flash(f"Successfully imported {success_count} medications", "success")
        else:
            flash("No medications were imported", "warning")
    else:
        flash(f"Import of {import_type} is not yet implemented", "warning")

    # Clean up temporary file
    os.unlink(file_path)
    os.rmdir(temp_dir)

    return redirect(url_for("settings.advanced"))


@settings_bp.route("/optimize", methods=["POST"])
def optimize_db():
    """Optimize the database for better performance."""
    logger.info("Optimizing database")

    success, message = optimize_database()

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("settings.advanced"))


@settings_bp.route("/clear_logs", methods=["POST"])
def clear_logs():
    """Clear old inventory logs to save space."""
    days_to_keep = int(request.form.get("days_to_keep", 90))
    logger.info(f"Clearing logs older than {days_to_keep} days")

    if days_to_keep < 30:
        flash("Please keep at least 30 days of logs", "warning")
        return redirect(url_for("settings.advanced"))

    deleted_count = clear_old_inventory_logs(days_to_keep)

    flash(f"Successfully removed {deleted_count} old inventory logs", "success")
    return redirect(url_for("settings.advanced"))


@settings_bp.route("/reset_data", methods=["POST"])
def reset_data():
    """Reset all application data (dangerous operation)."""
    verification = request.form.get("verification_text", "")
    logger.warning(f"Data reset requested. Verification: '{verification}'")

    if verification.lower() != "reset all data":
        flash("Verification text doesn't match. Data was not reset.", "warning")
        return redirect(url_for("settings.advanced"))

    try:
        # Backup the database first
        backup_path = create_database_backup()
        flash(f"Backup created at {backup_path}", "info")

        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        logger.warning("All data has been reset")
        flash(
            "All data has been reset. The application has been restored to initial state.",
            "success",
        )
    except Exception as e:
        logger.error(f"Error resetting data: {str(e)}")
        flash(f"Error resetting data: {str(e)}", "error")

    return redirect(url_for("index"))


@settings_bp.route("/update_timezone", methods=["POST"])
def update_timezone():
    """
    Update application timezone setting.
    """
    timezone_name = request.form.get("timezone_name", "UTC")
    logger.info(f"Updating timezone to: {timezone_name}")

    # Validate timezone
    try:
        valid = validate_timezone(timezone_name)
        if not valid:
            raise ValueError(f"Invalid timezone name: {timezone_name}")

        pytz.timezone(timezone_name)
    except Exception as e:
        logger.error(f"Invalid timezone: {timezone_name}. Error: {e}")
        flash(f"Invalid timezone: {timezone_name}", "error")
        return redirect(url_for("settings.advanced"))

    settings = HospitalVisitSettings.get_settings()
    settings.timezone_name = timezone_name
    db.session.commit()

    flash(f"Application timezone updated to {timezone_name}", "success")
    return redirect(url_for("settings.advanced"))


@settings_bp.route("/data_management")
def data_management():
    """
    Data management page with import/export/reset options for all data classes.
    """
    logger.info("Loading data management page")

    # Get database statistics
    med_count = Medication.query.count()
    inventory_count = Inventory.query.count()
    visit_count = HospitalVisit.query.count()
    order_count = Order.query.count()
    order_item_count = OrderItem.query.count()
    schedule_count = MedicationSchedule.query.count()

    # Get database path for display
    db_path = os.path.join("data", "medication_tracker.db")

    # Get database size
    db_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
    db_size_mb = (
        round(os.path.getsize(db_file_path) / (1024 * 1024), 2)
        if os.path.exists(db_file_path)
        else 0
    )

    return render_template(
        "settings/data_management.html",
        med_count=med_count,
        inventory_count=inventory_count,
        visit_count=visit_count,
        order_count=order_count,
        order_item_count=order_item_count,
        schedule_count=schedule_count,
        db_path=db_path,
        db_size_mb=db_size_mb,
    )


@settings_bp.route("/import/<data_type>", methods=["POST"])
def import_data_type(data_type: str):
    """
    Import data from an uploaded CSV file for a specific data type.

    Args:
        data_type: Type of data to import (medications, inventory, orders, visits)
    """
    logger.info(f"Handling data import for type: {data_type}")

    if "file" not in request.files:
        flash("No file part", "error")
        return redirect(url_for("settings.data_management"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("settings.data_management"))

    # Save the file to a temporary location
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(file_path)

    # Check if override option is selected
    override = "override" in request.form

    try:
        # Import based on data type
        if data_type == "medications":
            success_count, errors = import_medications_from_csv(file_path, override)
        elif data_type == "inventory":
            from data_utils import import_inventory_from_csv

            success_count, errors = import_inventory_from_csv(file_path, override)
        elif data_type == "orders":
            from data_utils import import_orders_from_csv

            success_count, errors = import_orders_from_csv(file_path, override)
        elif data_type == "visits":
            from data_utils import import_visits_from_csv

            success_count, errors = import_visits_from_csv(file_path, override)
        elif data_type == "schedules":
            from data_utils import import_schedules_from_csv

            success_count, errors = import_schedules_from_csv(file_path, override)
        else:
            flash(f"Unknown import type: {data_type}", "error")
            return redirect(url_for("settings.data_management"))

        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, "warning")
            if len(errors) > 5:
                flash(f"...and {len(errors) - 5} more errors", "warning")

        if success_count > 0:
            flash(
                f"Successfully imported {success_count} {data_type} records", "success"
            )
        else:
            flash(f"No {data_type} were imported", "warning")
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        flash(f"Error during import: {str(e)}", "error")
    finally:
        # Clean up temporary file
        os.unlink(file_path)
        os.rmdir(temp_dir)

    return redirect(url_for("settings.data_management"))


@settings_bp.route("/reset/<data_type>", methods=["POST"])
def reset_data_type(data_type: str):
    """
    Reset data for a specific data type.

    Args:
        data_type: Type of data to reset (medications, inventory, orders, visits)
    """
    logger.warning(f"Resetting data for type: {data_type}")

    verification = request.form.get("verification_text", "")
    expected_text = f"reset {data_type}"

    if verification.lower() != expected_text:
        flash(
            f"Verification text doesn't match. Expected '{expected_text}'. Data was not reset.",
            "warning",
        )
        return redirect(url_for("settings.data_management"))

    try:
        if data_type == "medications":
            # For medications we first need to delete related data
            from data_utils import reset_inventory_data, reset_orders_data

            reset_orders_data()  # Delete orders first
            reset_inventory_data()  # Then inventory

            # Then delete medications and recreate empty db
            Medication.query.delete()
            db.session.commit()

            flash("All medication data has been reset", "success")

        elif data_type == "inventory":
            from data_utils import reset_inventory_data

            count = reset_inventory_data()
            flash(f"All inventory data has been reset ({count} records)", "success")

        elif data_type == "orders":
            from data_utils import reset_orders_data

            count = reset_orders_data()
            flash(f"All order data has been reset ({count} records)", "success")

        elif data_type == "visits":
            from data_utils import reset_visits_data

            count = reset_visits_data()
            flash(f"All visit data has been reset ({count} records)", "success")

        elif data_type == "schedules":
            from data_utils import reset_schedules_data

            count = reset_schedules_data()
            flash(f"All schedule data has been reset ({count} records)", "success")

        else:
            flash(f"Unknown data type: {data_type}", "error")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting {data_type}: {str(e)}")
        flash(f"Error resetting {data_type}: {str(e)}", "error")

    return redirect(url_for("settings.data_management"))
