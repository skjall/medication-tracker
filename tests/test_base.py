"""
Base test class for all tests in the Medication Tracker application.

This module provides a BaseTestCase class that handles:
1. Setting up and tearing down the test database
2. Managing Flask app context
3. Common testing utilities

All test classes should inherit from this base class.
"""

# Standard library imports
import logging
import os
import sys
import unittest
from datetime import datetime, timezone

# Add app directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../app")))

logger = logging.getLogger("test_base")
logger.setLevel(logging.DEBUG)


class BaseTestCase(unittest.TestCase):
    """Base test class for all tests in the application."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class with a shared app context."""

        # Set up root logger
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Configure all existing loggers
        for logger_name in logging.root.manager.loggerDict:
            if logger_name.startswith("sqlalchemy."):
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.WARNING)
            else:
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.DEBUG)

        # Create a test app with scheduler disabled
        from app.main import create_app

        cls.app = create_app(
            {
                "TESTING": True,
                "SCHEDULER_AUTO_START": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )

        # Push app context
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        # Use the db instance that was initialized in create_app
        # This is the key change - use the db attached to app
        cls.db = cls.app.db

        # Create all tables
        cls.db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Clean up the test class."""
        # Shutdown the scheduler if it exists
        if hasattr(cls.app, "scheduler"):
            cls.app.scheduler.shutdown()

        # Drop all database tables
        with cls.app.app_context():
            cls.db.session.remove()
            cls.db.drop_all()

        # Pop the app context
        cls.app_context.pop()

    def setUp(self):
        """Set up test fixtures for each test."""
        self.db.session.begin_nested()  # Create a savepoint

        # Set current date to now (UTC for consistency in tests)
        self.now = datetime.now(timezone.utc)

        # Import models after app context is created
        from app.models import (
            MedicationSchedule,
            Medication,
            Inventory,
            Settings,
            PhysicianVisit,
            Order,
            OrderItem,
            Physician,
        )

        # Clean up any existing data to prevent test interference - using db session directly
        try:
            self.db.session.execute(self.db.delete(MedicationSchedule))
            self.db.session.execute(self.db.delete(Inventory))
            self.db.session.execute(self.db.delete(Medication))
            self.db.session.execute(self.db.delete(Settings))
            self.db.session.execute(self.db.delete(PhysicianVisit))
            self.db.session.execute(self.db.delete(Order))
            self.db.session.execute(self.db.delete(OrderItem))
            self.db.session.execute(self.db.delete(Physician))
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            print(f"Error cleaning up database: {e}")

    def tearDown(self):
        """Clean up after each test."""
        self.db.session.rollback()  # Roll back to the savepoint
        self.db.session.remove()
