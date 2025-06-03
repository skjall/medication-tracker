"""
Utilities for database migration using Alembic.

This module provides functions to handle database schema migrations
when the application starts or when explicitly triggered.
"""

# Standard library imports
import logging
import os
# subprocess not used
from typing import List, Tuple

# Third-party imports
from alembic import command
from alembic.config import Config
from flask import Flask

# Create a logger for this module
logger = logging.getLogger(__name__)

initial_revision = "d8942309667d"  # Initial revision ID for the database


def get_alembic_config(app: Flask) -> Config:
    """
    Create an Alembic configuration object based on Flask app settings.

    Args:
        app: Flask application instance

    Returns:
        Configured Alembic Config object
    """
    # Create Alembic config
    config_path = os.path.join(app.root_path, "..", "alembic.ini")
    alembic_cfg = Config(config_path)

    # Set SQLAlchemy URL from app config
    db_url = app.config["SQLALCHEMY_DATABASE_URI"]

    # Convert sqlite:/// URLs to absolute paths when necessary
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        # Handle relative path for SQLite
        db_path = db_url.replace("sqlite:///", "")
        abs_db_path = os.path.join(app.root_path, db_path)
        db_url = f"sqlite:///{abs_db_path}"

    # Set SQLAlchemy URL in Alembic config
    section = alembic_cfg.config_ini_section
    alembic_cfg.set_section_option(section, "sqlalchemy.url", db_url)

    # Set script location
    migrations_dir = os.path.join(app.root_path, "..", "migrations")
    alembic_cfg.set_main_option("script_location", migrations_dir)

    return alembic_cfg


def check_and_fix_version_tracking(app: Flask) -> bool:
    """
    Check if database has no alembic_version table, but an existing database file exists,
    and if so, stamp it with the initial revision.

    Args:
        app: Flask application instance

    Returns:
        True if stamping was performed, False otherwise
    """
    try:
        from sqlalchemy import create_engine, inspect, text
        import os.path

        # Get database URL
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]

        # First check if the database file exists (for SQLite)
        # For other database types, we'll assume the database exists if we can connect
        database_exists = True
        if db_url.startswith("sqlite:///"):
            # Extract file path for SQLite
            if db_url.startswith("sqlite:////"):  # Absolute path
                db_path = db_url[len("sqlite:///"):]
            else:  # Relative path
                db_path = db_url[len("sqlite:///"):]
                db_path = os.path.join(app.root_path, db_path)

            # Check if the file exists
            database_exists = os.path.isfile(db_path)
            logger.info(f"Checking for SQLite database at {db_path}: {'exists' if database_exists else 'not found'}")

            # If the database doesn't exist, don't try to stamp it
            if not database_exists:
                logger.info("No existing database file found - skipping version stamping")
                return False

        # Connect to the database (this might create a new SQLite file if it doesn't exist)
        engine = create_engine(db_url)

        # Get inspector
        inspector = inspect(engine)

        # Check if alembic_version exists
        existing_tables = inspector.get_table_names()
        has_alembic_version = "alembic_version" in existing_tables

        # Check if there are existing tables (indicating a real, pre-existing database)
        has_tables = len(existing_tables) > 0

        # If no alembic_version table but other tables exist, create it and stamp with initial revision
        if not has_alembic_version and has_tables:
            logger.info(f"Existing database detected without alembic_version table - stamping with initial revision {initial_revision}")

            # Create alembic_version table and stamp it directly
            with engine.connect() as conn:
                # First create the alembic_version table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))

                # Then insert the initial revision
                conn.execute(text(
                    f"INSERT INTO alembic_version (version_num) VALUES ('{initial_revision}')"
                ))

                # Commit the transaction
                conn.commit()

            logger.info(f"Successfully stamped database with revision {initial_revision}")
            return True
        elif has_alembic_version:
            logger.info("Database already has alembic_version table - checking for entries")

            # Check if the table is empty
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
                count = result.scalar()
                if count == 0 and has_tables:
                    logger.info(f"alembic_version table is empty in existing database - stamping with initial revision {initial_revision}")
                    conn.execute(text(
                        f"INSERT INTO alembic_version (version_num) VALUES ('{initial_revision}')"
                    ))
                    conn.commit()
                    logger.info(f"Successfully stamped database with revision {initial_revision}")
                    return True
                else:
                    logger.info("alembic_version table already has entries or database is new - no action needed")
        else:
            logger.info("New database detected (no tables) - no stamping needed")

        return False

    except Exception as e:
        logger.error(f"Error checking or fixing version tracking: {e}")
        return False


def check_migrations_needed(app: Flask) -> bool:
    """
    Check if database migrations are needed.

    Args:
        app: Flask application instance

    Returns:
        True if migrations are needed, False otherwise
    """
    try:
        from alembic.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine

        # Get database URL
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        engine = create_engine(db_url)

        # Check current revision in database
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()

        # Get latest revision in migration scripts
        config = get_alembic_config(app)
        script_dir = ScriptDirectory.from_config(config)
        head_rev = script_dir.get_current_head()

        # Compare revisions
        if current_rev != head_rev:
            logger.info(f"Database migration needed: current={current_rev}, latest={head_rev}")
            return True
        else:
            logger.info("Database is up to date.")
            return False

    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        # In case of error, assume migration might be needed
        return True


def run_migrations(app: Flask) -> bool:
    """
    Run database migrations using Alembic.

    Args:
        app: Flask application instance

    Returns:
        True if migrations were successful, False otherwise
    """
    try:
        logger.info("Running database migrations...")

        # Get Alembic config
        config = get_alembic_config(app)

        # Run the migration
        with app.app_context():
            command.upgrade(config, "head")

        logger.info("Database migrations completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def create_migration(app: Flask, message: str) -> bool:
    """
    Create a new migration script.

    Args:
        app: Flask application instance
        message: Migration message

    Returns:
        True if migration script was created successfully, False otherwise
    """
    try:
        logger.info(f"Creating migration: {message}")

        # Get Alembic config
        config = get_alembic_config(app)

        # Create new migration
        with app.app_context():
            command.revision(config, autogenerate=True, message=message)

        logger.info("Migration script created successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        return False


def get_migration_history(app: Flask) -> List[Tuple[str, str, str]]:
    """
    Get migration history.

    Args:
        app: Flask application instance

    Returns:
        List of tuples (revision_id, timestamp, description)
    """
    try:
        # Get Alembic config
        config = get_alembic_config(app)

        # Get script directory
        from alembic.script import ScriptDirectory
        script_dir = ScriptDirectory.from_config(config)

        # Get all revisions
        revisions = []
        for script in script_dir.walk_revisions():
            # Extract info from each revision
            rev_id = script.revision
            timestamp = script.doc.split("\n")[0] if script.doc else "Unknown"
            description = script.doc.split("\n")[2] if script.doc and len(script.doc.split("\n")) > 2 else "No description"

            revisions.append((rev_id, timestamp, description))

        return list(reversed(revisions))  # Latest first
    except Exception as e:
        logger.error(f"Failed to get migration history: {e}")
        return []


def initialize_migrations(app: Flask) -> bool:
    """
    Initialize the migrations environment if it doesn't exist.

    Args:
        app: Flask application instance

    Returns:
        True if initialization was successful or not needed, False otherwise
    """
    try:
        # First check and fix tracking if needed
        fix_applied = check_and_fix_version_tracking(app)
        if fix_applied:
            logger.info("Migration tracking fix applied, skipping initialization")
            return True

        # Check if migrations directory exists
        migrations_dir = os.path.join(app.root_path, "..", "migrations", "versions")
        if not os.path.exists(migrations_dir):
            logger.info("Initializing migrations environment...")
            os.makedirs(migrations_dir, exist_ok=True)

            # Get Alembic config
            config = get_alembic_config(app)

            # Initialize
            with app.app_context():
                command.init(config)

            logger.info("Migrations environment initialized.")

            # Create initial migration
            create_migration(app, "Initial migration")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize migrations: {e}")
        return False
