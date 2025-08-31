"""
Database initialization and migration handling module.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from models import (
    db,
    utcnow,
    ensure_timezone_utc,
    Medication,
    PhysicianVisit,
    Order,
    Inventory,
    InventoryLog,
    MedicationSchedule,
    Settings
)

logger = logging.getLogger(__name__)


def initialize_database(app):
    """Initialize database with migrations."""
    # Import here to avoid circular imports
    from migration_utils import stamp_database_to_latest, run_migrations_with_lock
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
        # Database exists with migration tracking
        # Run migrations unless explicitly disabled
        
        if os.environ.get('RUN_MIGRATIONS') != 'false':
            logger.info("Database already initialized with migration tracking - checking for pending migrations")
            if run_migrations_with_lock(app):
                logger.info("Migrations completed successfully")
            else:
                logger.warning("Migration run failed or timed out - continuing anyway")
        else:
            logger.debug("Skipping migrations (migrations disabled)")


def fix_database_timezones(app):
    """
    Update existing database records to ensure all datetime fields have timezone info.
    This is a one-time fix for existing data.
    """
    with app.app_context():
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


def check_upcoming_visits():
    """Check upcoming visits and perform any necessary actions."""
    logger.info("Checking upcoming visits")

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