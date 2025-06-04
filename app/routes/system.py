"""
Routes for system status and maintenance functions.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
import tzlocal
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)

# Local application imports
from utils import format_date, format_datetime, format_time, to_local_timezone
from migration_utils import check_migrations_needed, get_migration_history

# Logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for system routes
system_bp = Blueprint("system", __name__, url_prefix="/system")


@system_bp.route("/status")
def status():
    """
    Render a system status page with scheduler information.
    Displays the status of background tasks and system health.
    """
    from models import Settings

    settings = Settings.get_settings()

    # Check if scheduler is available in the app context
    scheduler_running = False
    tasks = []

    if hasattr(current_app, "scheduler"):
        logger.info("Scheduler is available in the app context.")
        scheduler = current_app.scheduler

        scheduler_running = scheduler.running

        # Log the status of the scheduler running:
        logger.info(f"Scheduler running: {scheduler_running}")

        # Get task information
        tasks = [
            {
                "name": name,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "interval": task.interval_seconds,
                "is_running": task.is_running,
            }
            for name, task in scheduler.tasks.items()
        ]
    else:
        logger.warning("Scheduler is not available in the app context.")

    # Get Python and Flask versions for display
    import platform
    import flask

    python_version = platform.python_version()
    flask_version = flask.__version__

    status = {
        "scheduler_running": scheduler_running,
        "tasks": tasks,
        "last_deduction_check": (
            settings.last_deduction_check if settings.last_deduction_check else None
        ),
    }

    local_timezone = tzlocal.get_localzone()
    local_server_time = datetime.now().astimezone(local_timezone)

    return render_template(
        "system/status.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        status=status,
        now=local_server_time,
        python_version=python_version,
        flask_version=flask_version,
        settings=settings,
        format_datetime=format_datetime,
        format_time=format_time,
        format_date=format_date,
    )


@system_bp.route("/restart_scheduler")
def restart_scheduler():
    """
    Restart the task scheduler.
    """
    if hasattr(current_app, "scheduler"):
        current_app.scheduler.restart()
        flash("Task scheduler has been restarted", "success")
    else:
        flash("Task scheduler not available", "error")


@system_bp.route("/detect_pipe_times")
def detect_pipe_times():
    """
    Detect and display medication schedules with pipe-separated times.
    This is a diagnostic tool for identifying data corruption issues.
    """
    from deduction_service import detect_pipe_separated_schedules
    
    try:
        problematic_schedules = detect_pipe_separated_schedules()
        
        if problematic_schedules:
            flash(f"Found {len(problematic_schedules)} schedules with pipe-separated times. Check logs for details.", "warning")
            for schedule_id, med_name, times_data in problematic_schedules:
                logger.warning(f"Schedule {schedule_id} ({med_name}): {times_data}")
        else:
            flash("No pipe-separated times detected in medication schedules.", "success")
            
    except Exception as e:
        logger.error(f"Error detecting pipe-separated times: {e}")
        flash(f"Error running detection: {e}", "error")
    
    return redirect(url_for("system.status"))


@system_bp.route("/fix_pipe_times")
def fix_pipe_times():
    """
    Detect and automatically fix medication schedules with pipe-separated times.
    This will permanently update the database to fix data corruption.
    """
    from deduction_service import detect_pipe_separated_schedules, get_and_fix_scheduled_times
    from models import MedicationSchedule
    
    try:
        # First detect all problematic schedules
        problematic_schedules = detect_pipe_separated_schedules()
        
        if not problematic_schedules:
            flash("No pipe-separated times detected in medication schedules.", "info")
            return redirect(url_for("system.status"))
        
        fixed_count = 0
        failed_count = 0
        
        for schedule_id, med_name, times_data in problematic_schedules:
            try:
                schedule = MedicationSchedule.query.get(schedule_id)
                if schedule:
                    # This will automatically detect and fix the pipe-separated times
                    corrected_times = get_and_fix_scheduled_times(schedule)
                    logger.info(f"Fixed schedule {schedule_id} ({med_name}): {corrected_times}")
                    fixed_count += 1
                else:
                    logger.error(f"Schedule {schedule_id} not found")
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to fix schedule {schedule_id}: {e}")
                failed_count += 1
        
        if fixed_count > 0:
            flash(f"Successfully fixed {fixed_count} schedules with pipe-separated times.", "success")
        if failed_count > 0:
            flash(f"Failed to fix {failed_count} schedules. Check logs for details.", "warning")
            
    except Exception as e:
        logger.error(f"Error fixing pipe-separated times: {e}")
        flash(f"Error running fix: {e}", "error")
    
    return redirect(url_for("system.status"))


@system_bp.route("/migrations")
def migrations():
    """
    Display database migration status and history.
    """
    logger.info("Accessing database migrations page")

    # Check if migrations are needed
    migrations_needed = check_migrations_needed(current_app)

    # Get migration history
    migration_history = get_migration_history(current_app)

    return render_template(
        "system/migrations.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        migrations_needed=migrations_needed,
        migration_history=migration_history,
    )


@system_bp.route("/run_migrations", methods=["POST"])
def run_db_migrations():
    """
    Run database migrations manually.
    """
    logger.info("Manual migration requested")

    from migration_utils import run_migrations

    success = run_migrations(current_app)

    if success:
        flash("Database migrations completed successfully", "success")
    else:
        flash("Error running database migrations", "error")

    return redirect(url_for("system.migrations"))
