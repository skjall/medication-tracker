"""
Main application module for the Medication Tracker application.
"""

import os
from datetime import datetime, timezone
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
    ensure_timezone_utc,
    utcnow,
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
    # Also create a backups directory
    os.makedirs(os.path.join(app.root_path, "data", "backups"), exist_ok=True)

    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.root_path, 'data', 'medication_tracker.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.environ.get("FLASK_ENV", "development") == "development",
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
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
    from routes.hospital_visit_settings import settings_bp
    from routes.schedule import schedule_bp
    from routes.advanced_settings import advanced_bp

    app.register_blueprint(medication_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(visit_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(advanced_bp)

    # Add utility functions to Jinja
    from utils import min_value, make_aware

    app.jinja_env.globals.update(min=min_value)
    app.jinja_env.globals.update(make_aware=make_aware)

    # Context processor to add date/time variables to all templates
    @app.context_processor
    def inject_now():
        # Important: Send a timezone-aware datetime to the templates
        return {"now": utcnow()}

    # Home route
    @app.route("/")
    def index():
        """Render the dashboard/home page."""
        medications = Medication.query.all()
        # Using the same filter as the visit page to ensure consistency
        upcoming_visit = (
            HospitalVisit.query.filter(HospitalVisit.visit_date >= utcnow())
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

    # Handle 404 errors
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors with a custom page."""
        return render_template("404.html"), 404

    return app


# After database initialization, ensure all existing datetimes have timezone info
def fix_database_timezones(app):
    """
    Update existing database records to ensure all datetime fields have timezone info.
    This is a one-time fix for existing data.
    """
    with app.app_context():
        try:
            # Fix HospitalVisit dates
            visits = HospitalVisit.query.all()
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
            from models import MedicationSchedule

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
            print("Successfully updated database with timezone information.")
        except Exception as e:
            print(f"Error updating database timezones: {e}")
            db.session.rollback()


# Application entry point
if __name__ == "__main__":
    app = create_app()
    # Fix existing data in the database if needed
    fix_database_timezones(app)

    # Start the automatic deduction thread
    from hospital_visit_utils import setup_auto_deduction

    auto_deduction_thread = setup_auto_deduction(app)

    port = int(os.environ.get("PORT", 8087))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
