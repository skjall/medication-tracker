"""
Initialization script for the database.

This module provides functions to initialize the database without sample data.
The sample data creation functions are kept for reference but not used by default.
"""

from models import db


def initialize_database() -> None:
    """Initialize database without sample data."""
    print("Initializing empty database...")
    # Only create tables, no sample data
    db.create_all()
    print("Database initialization complete!")


if __name__ == "__main__":
    # This can be run as a standalone script
    from main import create_app

    app = create_app()
    with app.app_context():
        # Only create tables
        initialize_database()
