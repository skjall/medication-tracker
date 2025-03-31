"""
Routes for system status and maintenance functions.
"""

from datetime import datetime, timezone
from utils import to_local_timezone, format_datetime

from flask import (
    Blueprint,
    render_template,
    current_app,
)

system_bp = Blueprint("system", __name__, url_prefix="/system")


@system_bp.route("/status")
def status():
    """
    Render a system status page with scheduler information.
    Displays the status of background tasks and system health.
    """
    from models import HospitalVisitSettings

    settings = HospitalVisitSettings.get_settings()

    # Check if scheduler is available in the app context
    scheduler_running = False
    tasks = []

    if hasattr(current_app, "scheduler"):
        scheduler = current_app.scheduler
        scheduler_running = scheduler.running

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

    # Get Python and Flask versions for display
    import platform
    import flask

    python_version = platform.python_version()
    flask_version = flask.__version__

    status = {
        "scheduler_running": scheduler_running,
        "tasks": tasks,
        "last_deduction_check": (
            settings.last_deduction_check.isoformat()
            if settings.last_deduction_check
            else None
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
    )
