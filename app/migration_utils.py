"""
Utilities for database migration using Alembic.

This module provides functions to handle database schema migrations
when the application starts or when explicitly triggered.
"""

# Standard library imports
import logging
import os
import time
from typing import List, Tuple

# Third-party imports
from alembic import command
from alembic.config import Config
from flask import Flask

# Create a logger for this module
logger = logging.getLogger(__name__)

initial_revision = "d8942309667d"  # Initial revision ID for the database


class MigrationLock:
    """Atomic file-based lock to ensure only one process runs migrations at a time."""

    def __init__(self, app: Flask):
        self.app = app
        # Check if running in Docker
        if os.path.exists('/app/data'):
            data_dir = '/app/data'
        else:
            data_dir = os.path.join(app.root_path, 'data')
        self.lock_file_path = os.path.join(data_dir, ".migration_lock")
        self.acquired = False

    def __enter__(self):
        """Acquire the migration lock using atomic file operations."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.lock_file_path), exist_ok=True)

            # Try to create lock file atomically
            # This will fail if file already exists (another process has lock)
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            lock_content = f"{timestamp}: PID {os.getpid()} acquired lock\n"

            # Use O_CREAT | O_EXCL for atomic lock acquisition
            try:
                fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.write(fd, lock_content.encode())
                os.close(fd)
                self.acquired = True
                logger.info(f"Migration lock acquired by process {os.getpid()}")
                return self
            except FileExistsError:
                # Lock already exists, check if it's stale
                if self._is_stale_lock():
                    # Remove stale lock and try again
                    try:
                        os.unlink(self.lock_file_path)
                        fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                        os.write(fd, lock_content.encode())
                        os.close(fd)
                        self.acquired = True
                        logger.info(f"Migration lock acquired by process {os.getpid()} after removing stale lock")
                        return self
                    except (FileExistsError, OSError):
                        pass

                # Could not acquire lock
                logger.info(f"Could not acquire migration lock (process {os.getpid()}): file exists")
                raise IOError("Migration lock already held")

        except Exception as e:
            logger.info(f"Could not acquire migration lock (process {os.getpid()}): {e}")
            raise

    def _is_stale_lock(self) -> bool:
        """Check if the lock file is stale (older than 5 minutes)."""
        try:
            if not os.path.exists(self.lock_file_path):
                return False
            # Check age of lock file
            lock_age = time.time() - os.path.getmtime(self.lock_file_path)
            return lock_age > 300  # 5 minutes
        except OSError:
            return True  # If we can't check, assume it's stale

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Release the migration lock."""
        # Unused parameters are part of context manager protocol
        _ = exc_type, exc_val, exc_tb
        if self.acquired:
            try:
                # Clean up lock file
                if os.path.exists(self.lock_file_path):
                    os.unlink(self.lock_file_path)
                logger.info(f"Migration lock released by process {os.getpid()}")
            except Exception as e:
                logger.warning(f"Error releasing migration lock: {e}")
            finally:
                self.acquired = False


def run_migrations_with_lock(app: Flask) -> bool:
    """
    Run migrations with file-based locking to prevent concurrent execution.
    Simplified to use standard Alembic without custom schema checks.

    Args:
        app: Flask application instance

    Returns:
        True if migrations were run or not needed, False if failed
    """
    try:
        # Try to acquire lock with timeout
        max_wait_time = 60  # 60 seconds max wait
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                with MigrationLock(app):
                    with app.app_context():
                        # Check if migrations are needed using standard Alembic
                        if not check_migrations_needed(app):
                            logger.info("No migrations needed - database is up to date")
                            return True

                        # Run the actual migrations
                        logger.info(f"Process {os.getpid()} running database migrations")
                        success = run_migrations(app)
                        if success:
                            logger.info("Database migrations completed successfully")
                        else:
                            logger.error("Database migrations failed")
                        return success

            except (IOError, OSError) as e:
                # Lock not available, wait and retry
                logger.info(f"Process {os.getpid()} waiting for migration lock: {e}")
                time.sleep(2)
                continue
            except Exception as e:
                logger.error(f"Unexpected error in migration lock for process {os.getpid()}: {e}")
                time.sleep(2)
                continue

        # Timeout reached
        logger.warning(f"Process {os.getpid()} timed out waiting for migration lock")
        return False

    except Exception as e:
        logger.error(f"Error in run_migrations_with_lock: {e}")
        return False


def get_alembic_config(app: Flask) -> Config:
    """
    Create an Alembic configuration object based on Flask app settings.

    Args:
        app: Flask application instance

    Returns:
        Configured Alembic Config object
    """
    # Create Alembic config
    # Check if we're in Docker (alembic.ini in same directory) or local dev (in parent)
    config_path = os.path.join(app.root_path, "alembic.ini")
    if not os.path.exists(config_path):
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
    # Check if we're in Docker (migrations in same directory) or local dev (in parent)
    migrations_dir = os.path.join(app.root_path, "migrations")
    if not os.path.exists(migrations_dir):
        migrations_dir = os.path.join(app.root_path, "..", "migrations")
    alembic_cfg.set_main_option("script_location", migrations_dir)

    return alembic_cfg


def verify_schema_integrity(app: Flask) -> bool:
    """
    Simplified schema verification - removed custom checks.
    Now just returns True to let Alembic handle everything.
    
    Returns:
        Always True - let Alembic manage schema state
    """
    logger.debug("Schema integrity check disabled - using standard Alembic")
    return True

def check_and_fix_version_tracking(app: Flask) -> bool:
    """
    Simplified version tracking - let Alembic handle version management.
    Only creates alembic_version table if missing but database has tables.

    Args:
        app: Flask application instance

    Returns:
        True if alembic_version table was created, False otherwise
    """
    try:
        from sqlalchemy import create_engine, inspect, text

        # Get database URL and connect
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        engine = create_engine(db_url)
        inspector = inspect(engine)

        # Check if alembic_version exists
        existing_tables = inspector.get_table_names()
        has_alembic_version = "alembic_version" in existing_tables
        has_tables = len(existing_tables) > 0

        # If no alembic_version table but other tables exist, create it
        # Let Alembic determine the correct version during migration
        if not has_alembic_version and has_tables:
            logger.info("Existing database without alembic_version table - creating table")
            
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))
                conn.commit()
            
            logger.info("Created alembic_version table - Alembic will determine correct version")
            return True

        return False

    except Exception as e:
        logger.error(f"Error checking version tracking: {e}")
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

        # Set environment variable to prevent double initialization
        os.environ['MIGRATION_IN_PROGRESS'] = '1'
        
        try:
            # Get Alembic config
            config = get_alembic_config(app)

            # Run the migration
            with app.app_context():
                command.upgrade(config, "head")

            logger.info("Database migrations completed successfully.")
            return True
        finally:
            # Always clean up the environment variable
            os.environ.pop('MIGRATION_IN_PROGRESS', None)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
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


def get_migration_history(app: Flask) -> List[Tuple[str, str, str, bool]]:
    """
    Get migration history with applied status.

    Args:
        app: Flask application instance

    Returns:
        List of tuples (revision_id, timestamp, description, is_applied)
    """
    try:
        # Get Alembic config
        config = get_alembic_config(app)

        # Get current database revision
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()

        # Get script directory
        from alembic.script import ScriptDirectory
        script_dir = ScriptDirectory.from_config(config)

        # Build revision tree to determine which are applied
        all_revisions = list(script_dir.walk_revisions())
        applied_revisions = set()
        
        # If we have a current revision, find all its ancestors
        if current_rev:
            for script in all_revisions:
                if script.revision == current_rev:
                    # Add this and all ancestors
                    applied_revisions.add(script.revision)
                    for ancestor in script_dir.iterate_revisions(current_rev, 'base'):
                        applied_revisions.add(ancestor.revision)
                    break

        # Get all revisions with status
        revisions = []
        for script in all_revisions:
            # Extract info from each revision
            rev_id = script.revision
            is_applied = rev_id in applied_revisions
            
            # Parse the migration file for better info
            import os
            
            timestamp = "Unknown"
            description = "No description"
            
            # Try to read the actual migration file for better info
            try:
                # The versions directory is in script_dir.dir + '/versions'
                versions_dir = os.path.join(script_dir.dir, 'versions')
                
                # Find the migration file - it starts with revision id
                for filename in os.listdir(versions_dir):
                    if filename.startswith(f"{rev_id}_") and filename.endswith('.py'):
                        # Extract description from filename
                        # Format: {rev_id}_{description}.py
                        desc_from_filename = filename[len(rev_id)+1:-3]  # Remove rev_id_ and .py
                        if desc_from_filename:
                            description = desc_from_filename.replace('_', ' ')
                        
                        # Read file for timestamp
                        filepath = os.path.join(versions_dir, filename)
                        with open(filepath, 'r') as f:
                            content = f.read()
                            # Extract timestamp
                            for line in content.split('\n'):
                                if 'Create Date:' in line:
                                    timestamp = line.split('Create Date:')[1].strip()
                                    break
                        break
            except Exception as e:
                logger.debug(f"Error reading migration file for {rev_id}: {e}")

            revisions.append((rev_id, timestamp, description, is_applied))

        return revisions  # Keep in order from newest to oldest
    except Exception as e:
        logger.error(f"Failed to get migration history: {e}")
        return []


def stamp_database_to_latest(app: Flask) -> bool:
    """
    Stamp the database to the latest migration version without running migrations.
    This is useful for fresh databases that have all tables created directly.
    
    Args:
        app: Flask application instance
    
    Returns:
        True if stamping was successful, False otherwise
    """
    try:
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine, text
        
        # Get the latest migration revision
        config = get_alembic_config(app)
        script_dir = ScriptDirectory.from_config(config)
        head_rev = script_dir.get_current_head()
        
        if not head_rev:
            logger.warning("No migration revisions found - cannot stamp database")
            return False
        
        logger.info(f"Stamping database to latest migration revision: {head_rev}")
        
        # Get database URL
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Create alembic_version table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
            """))
            
            # Clear any existing version (should be none for fresh database)
            conn.execute(text("DELETE FROM alembic_version"))
            
            # Insert the latest revision
            conn.execute(text(
                f"INSERT INTO alembic_version (version_num) VALUES ('{head_rev}')"
            ))
            
            conn.commit()
        
        logger.info(f"Successfully stamped database to revision {head_rev}")
        return True
        
    except Exception as e:
        logger.error(f"Error stamping database to latest: {e}")
        return False


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
        migrations_dir = os.path.join(app.root_path, "migrations", "versions")
        if not os.path.exists(migrations_dir):
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
