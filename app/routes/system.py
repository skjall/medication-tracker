"""
Routes for system status and maintenance functions.
"""

import logging

from datetime import datetime, timezone
from utils import to_local_timezone, format_datetime, format_time, format_date

from flask import (
    Blueprint,
    render_template,
    current_app,
    redirect,
    url_for,
    flash,
)

system_bp = Blueprint("system", __name__, url_prefix="/system")

# Logger for this module
logger = logging.getLogger(__name__)


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

    return render_template(
        "system/status.html",
        status=status,
        now=datetime.now(timezone.utc),
        local_time=to_local_timezone(datetime.now(timezone.utc)),
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

    return redirect(url_for("system.status"))
