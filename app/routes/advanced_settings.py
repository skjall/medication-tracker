"""
Routes for advanced settings and data management functions.
This is a partial fix that only addresses the timezone imports and functions.
"""

import os
import tempfile
import pytz
import logging

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    current_app,
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
)
from data_utils import (
    export_medications_to_csv,
    export_inventory_to_csv,
    export_orders_to_csv,
    export_visits_to_csv,
    create_database_backup,
    import_medications_from_csv,
    optimize_database,
    clear_old_inventory_logs,
)

# Fixed import: Use the correct path to timezone_helper
try:
    # Try a direct import first (in case the module is in PYTHONPATH)
    from timezone_helper import get_timezone_display_info, validate_timezone
except ImportError:
    # Fall back to a relative import (if the module is in the app package)
    try:
        from app.timezone_helper import get_timezone_display_info, validate_timezone
    except ImportError:
        # Last resort: implement the functions locally
        def get_timezone_display_info() -> List[Dict[str, str]]:
            """
            Get timezone display information including region and current offset.
            Fallback implementation if timezone_helper can't be imported.
            """
            now = datetime.now(timezone.utc)
            timezone_info = []

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
                except Exception:
                    # Skip invalid timezones
                    continue

            # Sort by region then offset
            return sorted(timezone_info, key=lambda x: (x["region"], x["offset"]))

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


advanced_bp = Blueprint("advanced", __name__, url_prefix="/advanced")


@advanced_bp.route("/export/<data_type>")
def export_data(data_type: str):
    """
    Export various data types to CSV.

    Args:
        data_type: Type of data to export (medications, inventory, orders, visits)
    """
    if data_type == "medications":
        return export_medications_to_csv()
    elif data_type == "inventory":
        return export_inventory_to_csv()
    elif data_type == "orders":
        return export_orders_to_csv()
    elif data_type == "visits":
        return export_visits_to_csv()
    else:
        flash(f"Unknown export type: {data_type}", "error")
        return redirect(url_for("settings.advanced"))


@advanced_bp.route("/backup")
def backup_database():
    """Create and download a backup of the database."""
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
        flash(f"Error creating backup: {str(e)}", "error")
        return redirect(url_for("settings.advanced"))


@advanced_bp.route("/import", methods=["POST"])
def import_data():
    """Import data from uploaded CSV files."""
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


@advanced_bp.route("/optimize", methods=["POST"])
def optimize_db():
    """Optimize the database for better performance."""
    success, message = optimize_database()

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("settings.advanced"))


@advanced_bp.route("/clear_logs", methods=["POST"])
def clear_logs():
    """Clear old inventory logs to save space."""
    days_to_keep = int(request.form.get("days_to_keep", 90))

    if days_to_keep < 30:
        flash("Please keep at least 30 days of logs", "warning")
        return redirect(url_for("settings.advanced"))

    deleted_count = clear_old_inventory_logs(days_to_keep)

    flash(f"Successfully removed {deleted_count} old inventory logs", "success")
    return redirect(url_for("settings.advanced"))


@advanced_bp.route("/reset_data", methods=["POST"])
def reset_data():
    """Reset all application data (dangerous operation)."""
    verification = request.form.get("verification_text", "")

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

        flash(
            "All data has been reset. The application has been restored to initial state.",
            "success",
        )
    except Exception as e:
        flash(f"Error resetting data: {str(e)}", "error")

    return redirect(url_for("index"))


@advanced_bp.route("/update_timezone", methods=["POST"])
def update_timezone():
    """
    Update application timezone setting.
    """
    timezone_name = request.form.get("timezone_name", "UTC")

    # Validate timezone
    try:
        pytz.timezone(timezone_name)
    except Exception as e:
        flash(f"Invalid timezone: {timezone_name}", "error")
        return redirect(url_for("settings.advanced"))

    settings = HospitalVisitSettings.get_settings()
    settings.timezone_name = timezone_name
    db.session.commit()

    flash(f"Application timezone updated to {timezone_name}", "success")
    return redirect(url_for("settings.advanced"))


@advanced_bp.route("/advanced", methods=["GET"])
def advanced():
    """
    Advanced settings page (e.g., backup/restore, system settings).
    """
    logging.info("Loading advanced settings page")

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
    logging.info("Getting timezone display information")
    timezone_info = get_timezone_display_info()

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
