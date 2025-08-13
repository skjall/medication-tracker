"""
Main application module for the Medication Tracker application.
"""

# Standard library imports
import logging
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone  # noqa: E402
from typing import Any, Dict, Optional  # noqa: E402

# Third-party imports
from flask import Flask, render_template, request  # noqa: E402

# Local application imports
from logging_config import configure_logging  # noqa: E402
from models import (  # noqa: E402
    db,
    utcnow,
    ensure_timezone_utc,
    Medication,
    PhysicianVisit,
    Order,
    Inventory,
    InventoryLog
)
from task_scheduler import TaskScheduler  # noqa: E402


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Factory function to create and configure the Flask application.

    Args:
        test_config: Optional configuration dictionary for testing

    Returns:
        Configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Ensure data directory exists
    os.makedirs(os.path.join(app.root_path, "data"), exist_ok=True)
    # Also create a backups directory
    os.makedirs(os.path.join(app.root_path, "data", "backups"), exist_ok=True)

    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "dev"
        ),  # Use a secure key in production
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.root_path, 'data', 'medication_tracker.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.environ.get("FLASK_ENV", "development") == "development",
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),  # Default log level
        SCHEDULER_AUTO_START=True,  # Auto-start the task scheduler
    )

    # Override config with test config if provided
    if test_config:
        app.config.update(test_config)

    # Configure logging
    logger = configure_logging(app)

    db.init_app(app)

    # Set up the database URI for SQLAlchemy
    app.db = db

    # Initialize task scheduler
    scheduler = TaskScheduler(app)

    # Initialize database with migrations
    with app.app_context():
        # Import here to avoid circular imports
        from migration_utils import stamp_database_to_latest
        from sqlalchemy import inspect
        
        # Check if this is a fresh database (no tables exist)
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables or len(existing_tables) == 0:
            # Fresh database - create all tables directly
            logger.info("Fresh database detected - creating all tables")
            try:
                db.create_all()
                logger.info("Database tables created successfully")
                
                # Stamp database to latest migration to skip running them
                stamp_database_to_latest(app)
                logger.info("Database stamped to latest migration version")
                
                # Create default settings
                from models.settings import Settings
                if not Settings.query.first():
                    default_settings = Settings()
                    db.session.add(default_settings)
                    db.session.commit()
                    logger.info("Default settings created")
                    
            except Exception as e:
                logger.error(f"Error creating database tables: {e}")
                # Continue anyway - some tables might have been created
        elif 'alembic_version' not in existing_tables:
            # Database exists but no migration tracking - stamp to latest
            logger.info("Existing database without migration tracking - stamping to latest")
            stamp_database_to_latest(app)
        else:
            # Database exists with migration tracking - run any pending migrations
            logger.info("Database already initialized with migration tracking - checking for pending migrations")
            from migration_utils import run_migrations_with_lock
            if run_migrations_with_lock(app):
                logger.info("Migrations completed successfully")
            else:
                logger.warning("Migration run failed or timed out - continuing anyway")

    # Register blueprints (routes)
    from routes.medications import medication_bp
    from routes.physicians import physician_bp
    from routes.inventory import inventory_bp
    from routes.visits import visit_bp
    from routes.orders import order_bp
    from routes.settings import settings_bp
    from routes.schedule import schedule_bp
    from routes.prescription_templates import prescription_bp
    from routes.system import system_bp

    app.register_blueprint(medication_bp)
    app.register_blueprint(physician_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(visit_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(prescription_bp)
    app.register_blueprint(system_bp)

    # Add utility functions to Jinja
    from utils import min_value, make_aware, format_date, format_datetime, format_time, to_local_timezone

    app.jinja_env.globals.update(min=min_value)
    app.jinja_env.globals.update(make_aware=make_aware)
    app.jinja_env.globals.update(format_date=format_date)
    app.jinja_env.globals.update(format_datetime=format_datetime)
    app.jinja_env.globals.update(format_time=format_time)
    app.jinja_env.globals.update(to_local_timezone=to_local_timezone)

    # Context processor to add date/time variables to all templates
    @app.context_processor
    def inject_now():
        # Get UTC time first
        utc_now = utcnow()

        # Convert to local timezone
        from utils import to_local_timezone

        local_now = to_local_timezone(utc_now)

        # Get settings for access in all templates
        from models import Settings

        settings = Settings.get_settings()

        # Return both UTC and local time, plus settings
        return {
            "now": local_now,  # Local time for display
            "utc_now": utc_now,  # UTC time for backend calculations
            "settings": settings,  # Application settings for templates
        }

    # Home route
    @app.route("/")
    def index():
        """Render the dashboard/home page."""
        logger.debug("Rendering dashboard page")
        medications = Medication.query.all()
        # Get ALL upcoming visits, not just the first one
        upcoming_visits = (
            PhysicianVisit.query.filter(PhysicianVisit.visit_date >= utcnow())
            .order_by(PhysicianVisit.visit_date)
            .all()
        )
        
        # Keep the first visit for backward compatibility with templates
        upcoming_visit = upcoming_visits[0] if upcoming_visits else None

        low_inventory = []
        gap_coverage_by_visit = []  # List of dicts: {visit: visit_obj, medications: [med1, med2]}
        
        for med in medications:
            if med.inventory and med.inventory.is_low:
                low_inventory.append(med)
        
        # Check for gap coverage needs for each upcoming visit
        if upcoming_visits:
            from utils import ensure_timezone_utc
            
            for visit in upcoming_visits:
                visit_gap_medications = []
                
                for med in medications:
                    if (med.inventory and med.depletion_date and 
                        not med.is_otc and  # Exclude OTC medications
                        med.physician_id == visit.physician_id):  # Only medications for this specific physician
                        # Check if medication will run out before this visit
                        if ensure_timezone_utc(med.depletion_date) < ensure_timezone_utc(visit.visit_date):
                            visit_gap_medications.append(med)
                
                # Only add visits that have gap coverage needs
                if visit_gap_medications:
                    gap_coverage_by_visit.append({
                        'visit': visit,
                        'medications': visit_gap_medications
                    })

        return render_template(
            "index.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            medications=medications,
            upcoming_visit=upcoming_visit,
            low_inventory=low_inventory,
            gap_coverage_by_visit=gap_coverage_by_visit,
        )

    # Handle 404 errors
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors with a custom page."""
        logger.warning(f"Page not found: {request.path}")
        return render_template("404.html"), 404

    # Add scheduler tasks
    with app.app_context():
        # Register the enhanced auto-deduction task
        # We check for the enhanced version first, and fall back if not available
        try:
            # Try to import the new enhanced deduction service
            from deduction_service import perform_deductions

            # Use the enhanced version
            logger.info("Registering enhanced auto-deduction service")
            scheduler.add_task(
                name="auto_deduction",
                func=perform_deductions,
                interval_seconds=3600,  # 1 hour
            )
        except ImportError:
            # Fall back to the legacy auto-deduction method
            logger.warning(
                "Enhanced deduction service not available, using legacy auto-deduction"
            )
            from physician_visit_utils import auto_deduct_inventory

            scheduler.add_task(
                name="auto_deduction",
                func=auto_deduct_inventory,
                interval_seconds=3600,  # 1 hour
            )

        # Add task to check for upcoming visits (every 12 hours)
        scheduler.add_task(
            name="check_upcoming_visits",
            func=check_upcoming_visits,
            interval_seconds=43200,  # 12 hours
        )

        logger.info("Scheduled background tasks registered")

    @app.template_filter("datetime")
    def parse_datetime(value):
        """Parse an ISO format datetime string into a datetime object."""
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            # If the string doesn't match ISO format, return current time as fallback
            return datetime.now(timezone.utc)

    return app


# Simple function to check upcoming visits and perform any necessary actions
def check_upcoming_visits():
    """Check upcoming visits and perform any necessary actions."""
    logger = logging.getLogger(__name__)
    logger.info("Checking upcoming visits")

    from models import PhysicianVisit, utcnow

    # Get visits in the next 7 days
    now = utcnow()
    one_week_later = now + timedelta(days=7)

    upcoming = (
        PhysicianVisit.query.filter(
            PhysicianVisit.visit_date >= now,
            PhysicianVisit.visit_date <= one_week_later,
        )
        .order_by(PhysicianVisit.visit_date)
        .all()
    )

    logger.info(f"Found {len(upcoming)} visits in the next 7 days")

    # This is where we could add code to send notifications
    # or perform other actions based on upcoming visits

    return len(upcoming)


# After database initialization, ensure all existing datetimes have timezone info
def fix_database_timezones(app):
    """
    Update existing database records to ensure all datetime fields have timezone info.
    This is a one-time fix for existing data.
    """
    with app.app_context():
        logger = logging.getLogger(__name__)
        logger.info("Running timezone fix for database records")

        try:
            # Fix PhysicianVisit dates
            visits = PhysicianVisit.query.all()
            for visit in visits:
                visit.visit_date = ensure_timezone_utc(visit.visit_date)
                visit.created_at = ensure_timezone_utc(visit.created_at)
                visit.updated_at = ensure_timezone_utc(visit.updated_at)

            # Fix Order dates
            orders = Order.query.all()
            for order in orders:
                order.created_date = ensure_timezone_utc(order.created_date)

            # Fix Inventory dates
            inventories = Inventory.query.all()
            for inv in inventories:
                inv.last_updated = ensure_timezone_utc(inv.last_updated)

            # Fix InventoryLog dates
            logs = InventoryLog.query.all()
            for log in logs:
                log.timestamp = ensure_timezone_utc(log.timestamp)

            # Fix MedicationSchedule dates
            from models import MedicationSchedule

            schedules = MedicationSchedule.query.all()
            for schedule in schedules:
                if schedule.last_deduction:
                    schedule.last_deduction = ensure_timezone_utc(
                        schedule.last_deduction
                    )
                schedule.created_at = ensure_timezone_utc(schedule.created_at)
                schedule.updated_at = ensure_timezone_utc(schedule.updated_at)

            # Fix Medication dates
            medications = Medication.query.all()
            for med in medications:
                med.created_at = ensure_timezone_utc(med.created_at)
                med.updated_at = ensure_timezone_utc(med.updated_at)

            # Commit all changes
            db.session.commit()
            logger.info("Successfully updated database with timezone information.")
        except Exception as e:
            logger.error(f"Error updating database timezones: {e}")
            db.session.rollback()


# Application entry point
if __name__ == "__main__":
    app = create_app()

    # Get logger
    logger = logging.getLogger(__name__)

    # Fix existing data in the database if needed
    fix_database_timezones(app)

    # Start the application
    port = int(os.environ.get("PORT", 8087))
    logger.info(f"Starting Medication Tracker on port {port}")
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
