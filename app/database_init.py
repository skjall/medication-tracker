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
    PhysicianVisit,
    Order,
    MedicationSchedule,
    Settings
)

logger = logging.getLogger(__name__)


def initialize_database(app):
    """Initialize database with migrations using standard Alembic."""
    # Import here to avoid circular imports
    from migration_utils import stamp_database_to_latest, run_migrations_with_lock, check_and_fix_version_tracking
    from sqlalchemy import inspect
    
    # Check if this is a fresh database (no tables exist)
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    if not existing_tables or len(existing_tables) == 0:
        # Fresh database - create all tables and stamp to latest
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
    else:
        # Database exists - ensure migration tracking and run migrations
        logger.info("Existing database detected - checking migration status")
        
        # Ensure alembic_version table exists
        check_and_fix_version_tracking(app)
        
        # Run migrations unless explicitly disabled
        if os.environ.get('RUN_MIGRATIONS') != 'false':
            logger.info("Checking for pending migrations")
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


            # Fix MedicationSchedule dates
            schedules = MedicationSchedule.query.all()
            for schedule in schedules:
                if schedule.last_deduction:
                    schedule.last_deduction = ensure_timezone_utc(
                        schedule.last_deduction
                    )
                schedule.created_at = ensure_timezone_utc(schedule.created_at)
                schedule.updated_at = ensure_timezone_utc(schedule.updated_at)


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