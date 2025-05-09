from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
import importlib

# Add the project root and app directories to the Python path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, "app"))

# Import Flask app to ensure proper initialization
from app import create_app
from app.models.base import db

# Create Flask app to ensure all models are loaded
app = create_app()
# Use app context to load models
with app.app_context():
    # Dynamically import all modules in the models package
    import app.models

    # Remove reload of models to avoid re-defining tables
    # Simply import to ensure they are loaded

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata to the SQLAlchemy models' metadata
target_metadata = db.metadata

# Dynamically set the sqlalchemy.url if not already set
def get_database_path():
    """
    Determine the absolute path for the SQLite database file.
    Creates the necessary directories if they don't exist.
    """
    # Construct the SQLite database path
    db_path = os.path.join(base_dir, 'app', 'data', 'medication_tracker.db')

    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    return f'sqlite:///{db_path}'

# Set the database URL
database_url = get_database_path()
config.set_main_option('sqlalchemy.url', database_url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use the configuration from the config to create an engine
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

# Ensure the database file can be created before running migrations
def ensure_database_path():
    try:
        # Try to create the database file's directory
        os.makedirs(os.path.dirname(database_url.replace('sqlite:///', '')), exist_ok=True)
    except Exception as e:
        print(f"Error creating database directory: {e}")
        raise

# Call this before running migrations
ensure_database_path()

# Run migrations based on mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()