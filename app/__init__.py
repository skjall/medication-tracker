from flask import Flask
from .models.base import db


def create_app(config_name=None):
    """
    Create and configure the Flask application.

    :param config_name: Optional configuration name (e.g., 'development', 'production')
    :return: Configured Flask application
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Configure the SQLite database path
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/medication_tracker.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Optional: Add any other configurations or blueprint registrations here

    return app
