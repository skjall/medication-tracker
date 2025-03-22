"""
Main application module for the Medication Tracker application.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

from models import (
    db,
    Medication,
    Inventory,
    InventoryLog,
    HospitalVisit,
    Order,
    OrderItem,
)


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

    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.root_path, 'data', 'medication_tracker.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.environ.get("FLASK_ENV", "development") == "development",
    )

    # Override config with test config if provided
    if test_config:
        app.config.update(test_config)

    # Initialize database
    db.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints (routes)
    from routes.medications import medication_bp
    from routes.inventory import inventory_bp
    from routes.visits import visit_bp
    from routes.orders import order_bp

    app.register_blueprint(medication_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(visit_bp)
    app.register_blueprint(order_bp)

    # Context processor to add date/time variables to all templates
    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}

    # Home route
    @app.route("/")
    def index():
        """Render the dashboard/home page."""
        medications = Medication.query.all()
        upcoming_visit = (
            HospitalVisit.query.filter(HospitalVisit.visit_date > datetime.utcnow())
            .order_by(HospitalVisit.visit_date)
            .first()
        )

        low_inventory = []
        for med in medications:
            if med.inventory and med.inventory.is_low:
                low_inventory.append(med)

        return render_template(
            "index.html",
            medications=medications,
            upcoming_visit=upcoming_visit,
            low_inventory=low_inventory,
        )

    return app


# Application entry point
if __name__ == "__main__":
    app = create_app()
    # Use 0.0.0.0 to make the server accessible from outside the container
    app.run(host="0.0.0.0", port=8080, debug=True)
