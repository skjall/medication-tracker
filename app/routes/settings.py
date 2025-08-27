"""
Routes for managing application settings.

into a single unified settings module to avoid route conflicts.
"""

# Standard library imports
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from utils import to_local_timezone, get_data_directory

# Third-party imports
import pytz
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _
from werkzeug.utils import secure_filename

# Local application imports
from data_utils import (
    clear_old_inventory_logs,
    create_database_backup,
    export_inventory_to_csv,
    export_medications_to_csv,
    export_orders_to_csv,
    export_physicians_to_csv,
    export_schedules_to_csv,
    export_visits_to_csv,
    import_medications_from_csv,
    import_physicians_from_csv,
    optimize_database,
)
from version import get_version
from models import (
    Inventory,
    InventoryLog,
    PhysicianVisit,
    Physician,
    Medication,
    MedicationSchedule,
    Order,
    OrderItem,
    Settings,
    db,
)
from timezone_helper import get_timezone_display_info, validate_timezone

# Logger for this module
logger = logging.getLogger(__name__)


# Create a single settings blueprint to combine both previous routes
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/physician_visits", methods=["GET", "POST"])
def physician_visits():
    """
    Display and update physician visit settings.
    """
    logger.info("Accessing physician visit settings page")

    # Get current settings
    settings = Settings.get_settings()

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

        flash(_("Physician visit settings updated successfully"), "success")
        return redirect(url_for("settings.physician_visits"))

    # Calculate actual average interval for information purposes
    from physician_visit_utils import calculate_days_between_visits

    actual_interval = calculate_days_between_visits()

    return render_template(
        "settings/physician_visits.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        settings=settings,
        actual_interval=actual_interval,
    )


@settings_bp.route(
    "/update_visit_order_planning/<int:visit_id>", methods=["POST"]
)
def update_visit_order_planning(visit_id: int):
    """
    Update the order planning setting for a specific visit.
    """
    logger.info(f"Updating order planning for visit {visit_id}")

    visit = PhysicianVisit.query.get_or_404(visit_id)

    # Toggle the setting
    visit.order_for_next_but_one = not visit.order_for_next_but_one
    db.session.commit()

    if visit.order_for_next_but_one:
        message = _(
            "Orders for this visit will now be planned to last until the next-but-one visit"
        )
    else:
        message = _(
            "Orders for this visit will now be planned to last until the next visit only"
        )

    flash(message, "success")
    return redirect(url_for("visits.show", id=visit_id))


@settings_bp.route("/system", methods=["GET"])
def system():
    """
    System settings page focusing on timezone and automatic deduction settings.
    """
    logger.info("Loading system settings page")

    # Get settings
    settings = Settings.get_settings()

    # Get basic statistics for system status
    schedule_count = MedicationSchedule.query.count()
    upcoming_visits_count = PhysicianVisit.query.filter(
        PhysicianVisit.visit_date >= datetime.now(timezone.utc)
    ).count()

    # Get current version
    current_version = get_version()

    # Import timezone helper for getting timezone information
    logger.info("Getting timezone display information")
    try:
        timezone_info = get_timezone_display_info()
        logger.info(f"Got {len(timezone_info)} timezone entries")
    except Exception as e:
        logger.error(f"Error getting timezone display info: {e}")
        timezone_info = []

    return render_template(
        "settings/system.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        settings=settings,
        schedule_count=schedule_count,
        upcoming_visits_count=upcoming_visits_count,
        timezone_info=timezone_info,
        current_version=current_version,
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
    elif data_type == "physicians":
        return export_physicians_to_csv()
    else:
        flash(_("Unknown export type: {}").format(data_type), "error")
        return redirect(url_for("settings.system"))


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
        flash(_("Error creating backup: {}").format(str(e)), "error")
        return redirect(url_for("settings.system"))


@settings_bp.route("/restore", methods=["POST"])
def restore_database():
    """Restore database from an uploaded backup file."""
    logger.info("Handling database restore")

    # Check if user confirmed the restore
    if not request.form.get("confirm_restore"):
        flash(
            _(
                "You must confirm that you understand the restore will replace all current data"
            ),
            "error",
        )
        return redirect(url_for("settings.data_management"))

    if "restore_file" not in request.files:
        flash(_("No file provided for restore"), "error")
        return redirect(url_for("settings.data_management"))

    file = request.files["restore_file"]
    if file.filename == "":
        flash(_("No file selected"), "error")
        return redirect(url_for("settings.data_management"))

    # Validate file extension
    allowed_extensions = {".db", ".sqlite", ".sqlite3"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        flash(
            _("Invalid file type. Please upload a database file ({})").format(
                ", ".join(allowed_extensions)
            ),
            "error",
        )
        return redirect(url_for("settings.data_management"))

    try:
        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_file_path)

        # Validate that it's a valid SQLite database
        try:
            conn = sqlite3.connect(temp_file_path)
            cursor = conn.cursor()
            # Check if it has the expected tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='medications'"
            )
            if not cursor.fetchone():
                flash(
                    _("Invalid database file: missing required tables"),
                    "error",
                )
                return redirect(url_for("settings.data_management"))
            conn.close()
        except sqlite3.Error as e:
            flash(_("Invalid database file: {}").format(str(e)), "error")
            return redirect(url_for("settings.data_management"))

        # Create backup of current database before restore
        data_dir = get_data_directory()
        backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        current_db_path = os.path.join(
            data_dir, "medication_tracker.db"
        )
        pre_restore_backup = os.path.join(
            backup_dir,
            f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
        )

        # Close all database connections
        db.session.close_all()
        db.engine.dispose()

        # Create backup of current database
        shutil.copy2(current_db_path, pre_restore_backup)
        logger.info(f"Created pre-restore backup at: {pre_restore_backup}")

        # Replace current database with uploaded file
        shutil.copy2(temp_file_path, current_db_path)
        logger.info(f"Database restored from uploaded file")

        # Clean up temporary file
        os.unlink(temp_file_path)
        os.rmdir(temp_dir)

        # Force migration check after restore
        try:
            from migration_utils import (
                check_and_fix_version_tracking,
                run_migrations_with_lock,
            )

            logger.info(
                "Checking and applying migrations after database restore"
            )

            # Re-establish database connection with the new database
            db.engine.dispose()
            db.session.remove()
            
            # Import the verify function
            from migration_utils import verify_schema_integrity
            
            # Check if the restored database needs migration tracking
            check_and_fix_version_tracking(current_app)
            
            # Force schema integrity check - this will reset version if needed
            if not verify_schema_integrity(current_app):
                logger.info("Restored database has schema issues - forcing migration")

            # Run any pending migrations (will now check schema integrity)
            if run_migrations_with_lock(current_app):
                logger.info(
                    "Migrations applied successfully after database restore"
                )
            else:
                logger.warning(
                    "Migration check failed after restore - continuing anyway"
                )
            
            # Dispose and recreate connection again to ensure fresh schema
            db.engine.dispose()
            db.session.remove()

        except Exception as migration_error:
            logger.error(
                f"Error running migrations after restore: {migration_error}"
            )
            flash(
                _("Database restored but migration failed: {}").format(
                    migration_error
                ),
                "warning",
            )
            return redirect(url_for("settings.data_management"))

        flash(
            _("Database successfully restored and migrations applied!"),
            "success",
        )
        logger.info("Database restore completed successfully with migrations")

        return redirect(url_for("settings.data_management"))

    except Exception as e:
        logger.error(f"Error restoring database: {str(e)}")
        flash(_("Error restoring database: {}").format(str(e)), "error")
        return redirect(url_for("settings.data_management"))


@settings_bp.route("/import", methods=["POST"])
def import_data():
    """Import data from uploaded CSV files."""
    logger.info("Handling data import")

    if "file" not in request.files:
        flash(_("No file part"), "error")
        return redirect(url_for("settings.system"))

    file = request.files["file"]
    if file.filename == "":
        flash(_("No file selected"), "error")
        return redirect(url_for("settings.system"))

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
                flash(
                    _("... and {} more errors").format(len(errors) - 5),
                    "warning",
                )

        if success_count > 0:
            flash(
                _("Successfully imported {} medications").format(
                    success_count
                ),
                "success",
            )
        else:
            flash(_("No medications were imported"), "warning")
    else:
        flash(
            _("Import of {} is not yet implemented").format(import_type),
            "warning",
        )

    # Clean up temporary file
    os.unlink(file_path)
    os.rmdir(temp_dir)

    return redirect(url_for("settings.system"))


@settings_bp.route("/optimize", methods=["POST"])
def optimize_db():
    """Optimize the database for better performance."""
    logger.info("Optimizing database")

    success, message = optimize_database()

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("settings.data_management"))


@settings_bp.route("/clear_logs", methods=["POST"])
def clear_logs():
    """Clear old inventory logs to save space."""
    days_to_keep = int(request.form.get("days_to_keep", 90))
    logger.info(f"Clearing logs older than {days_to_keep} days")

    if days_to_keep < 30:
        flash(_("Please keep at least 30 days of logs"), "warning")
        return redirect(url_for("settings.data_management"))

    deleted_count = clear_old_inventory_logs(days_to_keep)

    flash(
        _("Successfully removed {} old inventory logs").format(deleted_count),
        "success",
    )
    return redirect(url_for("settings.data_management"))


@settings_bp.route("/reset_data", methods=["POST"])
def reset_data():
    """Reset all application data (dangerous operation)."""
    verification = request.form.get("verification_text", "")
    logger.warning(f"Data reset requested. Verification: '{verification}'")

    if verification.lower() != "reset all data":
        flash(
            _("Verification text doesn't match. Data was not reset."),
            "warning",
        )
        return redirect(url_for("settings.system"))

    try:
        # Backup the database first
        backup_path = create_database_backup()
        flash(_("Backup created at {}").format(backup_path), "info")

        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        logger.warning("All data has been reset")
        flash(
            _(
                "All data has been reset. The application has been restored to initial state."
            ),
            "success",
        )
    except Exception as e:
        logger.error(f"Error resetting data: {str(e)}")
        flash(_("Error resetting data: {}").format(str(e)), "error")

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
        flash(_("Invalid timezone: {}").format(timezone_name), "error")
        return redirect(url_for("settings.system"))

    settings = Settings.get_settings()
    settings.timezone_name = timezone_name
    db.session.commit()

    flash(
        _("Application timezone updated to {}").format(timezone_name),
        "success",
    )
    return redirect(url_for("settings.system"))


@settings_bp.route("/data_management")
def data_management():
    """
    Data management page with import/export/reset options for all data classes.
    """
    logger.info("Loading data management page")

    # Get database statistics with error handling for missing columns
    def safe_count(model, model_name):
        """Safely count records, returning 0 if there's a database error."""
        try:
            return model.query.count()
        except Exception as e:
            logger.warning(f"Could not count {model_name}: {e}")
            # Try to trigger migration if there's a schema issue
            if "no such column" in str(e).lower():
                logger.info(f"Schema issue detected for {model_name}, attempting migration")
                try:
                    from migration_utils import run_migrations_with_lock
                    run_migrations_with_lock(current_app)
                except Exception as migration_error:
                    logger.error(f"Auto-migration failed: {migration_error}")
            return 0

    # Count new data models
    from models import ActiveIngredient, MedicationProduct, PackageInventory
    
    ingredient_count = safe_count(ActiveIngredient, "active_ingredients")
    product_count = safe_count(MedicationProduct, "medication_products")
    package_count = safe_count(PackageInventory, "package_inventories")
    
    # Count existing models
    visit_count = safe_count(PhysicianVisit, "visits")
    physician_count = safe_count(Physician, "physicians")
    order_count = safe_count(Order, "orders")
    order_item_count = safe_count(OrderItem, "order_items")
    inventory_logs_count = safe_count(InventoryLog, "inventory_logs")

    # Get database path for display
    data_dir = get_data_directory()
    db_path = os.path.join(data_dir, "medication_tracker.db")

    # Get database size - in Docker, the database is in the app directory
    db_file_path = os.path.join(current_app.root_path, db_path)

    if os.path.exists(db_file_path):
        size_bytes = os.path.getsize(db_file_path)
        size_mb = size_bytes / (1024 * 1024)

        if size_mb >= 1:
            db_size = round(size_mb, 2)
            db_size_unit = "MB"
        else:
            db_size = round(size_bytes / 1024, 1)
            db_size_unit = "KB"
    else:
        logger.warning(f"Database file not found at: {db_file_path}")
        db_size = 0
        db_size_unit = "KB"

    return render_template(
        "settings/data_management.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        ingredient_count=ingredient_count,
        product_count=product_count,
        package_count=package_count,
        visit_count=visit_count,
        physician_count=physician_count,
        order_count=order_count,
        order_item_count=order_item_count,
        inventory_logs_count=inventory_logs_count,
        db_path=db_path,
        db_size=db_size,
        db_size_unit=db_size_unit,
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
        flash(_("No file part"), "error")
        return redirect(url_for("settings.data_management"))

    file = request.files["file"]
    if file.filename == "":
        flash(_("No file selected"), "error")
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
            success_count, errors = import_medications_from_csv(
                file_path, override
            )
        elif data_type == "inventory":
            from data_utils import import_inventory_from_csv

            success_count, errors = import_inventory_from_csv(
                file_path, override
            )
        elif data_type == "orders":
            from data_utils import import_orders_from_csv

            success_count, errors = import_orders_from_csv(file_path, override)
        elif data_type == "visits":
            from data_utils import import_visits_from_csv

            success_count, errors = import_visits_from_csv(file_path, override)
        elif data_type == "schedules":
            from data_utils import import_schedules_from_csv

            success_count, errors = import_schedules_from_csv(
                file_path, override
            )
        elif data_type == "physicians":
            success_count, errors = import_physicians_from_csv(
                file_path, override
            )
        else:
            flash(_("Unknown import type: {}").format(data_type), "error")
            return redirect(url_for("settings.data_management"))

        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, "warning")
            if len(errors) > 5:
                flash(
                    _("... and {} more errors").format(len(errors) - 5),
                    "warning",
                )

        if success_count > 0:
            flash(
                _("Successfully imported {} {} records").format(
                    success_count, data_type
                ),
                "success",
            )
        else:
            flash(_("No {} were imported").format(data_type), "warning")
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        flash(_("Error during import: {}").format(str(e)), "error")
    finally:
        # Clean up temporary file
        os.unlink(file_path)
        os.rmdir(temp_dir)

    return redirect(url_for("settings.data_management"))


@settings_bp.route("/check_updates", methods=["GET"])
def check_updates():
    """
    Check for application updates by comparing with the latest GitHub release.
    """
    import requests
    import json

    logger.info("Checking for application updates")

    current_version = get_version()

    try:
        # Check GitHub API for latest release
        response = requests.get(
            "https://api.github.com/repos/skjall/medication-tracker/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=5,
        )

        if response.status_code == 200:
            release_data = response.json()
            latest_version = release_data.get("tag_name", "").lstrip("v")
            release_url = release_data.get("html_url", "")
            release_date = release_data.get("published_at", "")

            # Parse version numbers for comparison
            def parse_version(v):
                try:
                    return tuple(map(int, v.split(".")))
                except:
                    return (0, 0, 0)

            current = parse_version(current_version)
            latest = parse_version(latest_version)

            update_available = latest > current

            return jsonify(
                {
                    "success": True,
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "update_available": update_available,
                    "release_url": release_url,
                    "release_date": release_date,
                }
            )
        else:
            logger.warning(
                f"GitHub API returned status {response.status_code}"
            )
            return jsonify(
                {
                    "success": False,
                    "current_version": current_version,
                    "error": _("Unable to check for updates"),
                }
            )

    except requests.exceptions.Timeout:
        logger.error("Timeout while checking for updates")
        return jsonify(
            {
                "success": False,
                "current_version": current_version,
                "error": _("Connection timeout"),
            }
        )
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        return jsonify(
            {
                "success": False,
                "current_version": current_version,
                "error": "Unable to check for updates",
            }
        )


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
            _(
                "Verification text doesn't match. Expected '{}'. Data was not reset."
            ).format(expected_text),
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

            flash(_("All medication data has been reset"), "success")

        elif data_type == "inventory":
            from data_utils import reset_inventory_data

            count = reset_inventory_data()
            flash(
                _("All inventory data has been reset ({} records)").format(
                    count
                ),
                "success",
            )

        elif data_type == "orders":
            from data_utils import reset_orders_data

            count = reset_orders_data()
            flash(
                _("All order data has been reset ({} records)").format(count),
                "success",
            )

        elif data_type == "visits":
            from data_utils import reset_visits_data

            count = reset_visits_data()
            flash(
                _("All visit data has been reset ({} records)").format(count),
                "success",
            )

        elif data_type == "schedules":
            from data_utils import reset_schedules_data

            count = reset_schedules_data()
            flash(
                _("All schedule data has been reset ({} records)").format(
                    count
                ),
                "success",
            )

        elif data_type == "physicians":
            from data_utils import reset_physicians_data

            count = reset_physicians_data()
            flash(
                _("All physician data has been reset ({} records)").format(
                    count
                ),
                "success",
            )

        else:
            flash(_("Unknown data type: {}").format(data_type), "error")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting {data_type}: {str(e)}")
        flash(_("Error resetting {}: {}").format(data_type, str(e)), "error")

    return redirect(url_for("settings.data_management"))
