"""
Base test class for all tests in the Medication Tracker application.

This module provides a BaseTestCase class that handles:
1. Setting up and tearing down the test database
2. Managing Flask app context
3. Common testing utilities

All test classes should inherit from this base class.
"""

import os
import sys
import unittest

# Add app directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../app")))


class BaseTestCase(unittest.TestCase):
    """Base test class for all tests in the application."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class with a shared app context."""
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

        # Get the db instance that was initialized in create_app
        with cls.app.app_context():
            # Import models AFTER app context is pushed
            from app.models import db

            cls.db = db

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

    def tearDown(self):
        """Clean up after each test."""
        self.db.session.rollback()  # Roll back to the savepoint
        self.db.session.remove()
