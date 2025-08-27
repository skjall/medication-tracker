"""
Main application module for the Medication Tracker application.
"""

# Standard library imports
import logging
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone  # noqa: E402
from typing import Any, Dict, Optional  # noqa: E402

# Third-party imports
from flask import Flask, render_template, request  # noqa: E402

# Local application imports
from logging_config import configure_logging  # noqa: E402
from models import (  # noqa: E402
    db,
    utcnow,
    ensure_timezone_utc,
    Medication,
    PhysicianVisit,
    Physician,  # noqa: F401 - needed for db.create_all()
    OrderItem,  # noqa: F401 - needed for db.create_all()
    ScheduleType,  # noqa: F401 - needed for db.create_all()
    MedicationPackage,  # noqa: F401 - needed for db.create_all()
    ScannedItem,  # noqa: F401 - needed for db.create_all()
    PackageInventory  # noqa: F401 - needed for db.create_all()
)
from task_scheduler import TaskScheduler  # noqa: E402
from utils import to_local_timezone  # noqa: E402

# Import extracted modules
from translation_config import setup_babel, register_translation_routes  # noqa: E402
from database_init import initialize_database, fix_database_timezones, check_upcoming_visits  # noqa: E402
from route_registration import register_blueprints  # noqa: E402
from jinja_config import setup_jinja  # noqa: E402


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Factory function to create and configure the Flask application.

    Args:
        test_config: Optional configuration dictionary for testing

    Returns:
        Configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__)

    # Determine the correct data directory path
    # In Docker, use /app/data; locally use app.root_path/data
    if os.path.exists('/app/data'):
        # Running in Docker container
        data_dir = '/app/data'
    else:
        # Running locally
        data_dir = os.path.join(app.root_path, 'data')
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    # Also create a backups directory
    os.makedirs(os.path.join(data_dir, "backups"), exist_ok=True)

    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "dev"
        ),  # Use a secure key in production
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(data_dir, 'medication_tracker.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.environ.get("FLASK_ENV", "development") == "development",
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),  # Default log level
        SCHEDULER_AUTO_START=True,  # Auto-start the task scheduler
    )

    # Override config with test config if provided
    if test_config:
        app.config.update(test_config)

    # Configure logging
    logger = configure_logging(app)

    # Initialize database
    db.init_app(app)
    app.db = db

    # Setup Babel for internationalization
    setup_babel(app)
    register_translation_routes(app)

    # Initialize task scheduler
    scheduler = TaskScheduler(app)

    # Initialize database with migrations
    with app.app_context():
        initialize_database(app)

    # Register blueprints (routes)
    register_blueprints(app)

    # Setup Jinja configuration
    setup_jinja(app)
    
    # Register timezone template filters
    from template_filters import register_filters
    register_filters(app)

    # Home route
    @app.route("/test_translation")
    def test_translation():
        return render_template("test_translation.html")
    
    @app.route("/")
    def index():
        """Render the dashboard/home page."""
        from flask_babel import get_locale, gettext
        from models import ActiveIngredient, MedicationProduct
        current_locale = get_locale()
        logger.debug(f"Rendering dashboard page with locale: {current_locale}")
        
        # Test translation within request context
        test_translation = gettext('Dashboard')
        test_translation2 = gettext('No upcoming physician visits scheduled.')
        logger.debug(f"Translation test - 'Dashboard': '{test_translation}'")
        logger.debug(f"Translation test - 'No upcoming physician visits scheduled.': '{test_translation2}'")
        
        # Get all active ingredients instead of medications
        ingredients = ActiveIngredient.query.order_by(ActiveIngredient.name).all()
        
        # Group ingredients by physician or OTC status for display
        ingredients_by_physician = {}
        otc_ingredients = []
        
        for ingredient in ingredients:
            # Check if ingredient has any OTC products
            has_otc = any(product.is_otc for product in ingredient.products)
            if has_otc:
                otc_ingredients.append(ingredient)
            
            # Group by physician for prescription products
            for product in ingredient.products:
                if not product.is_otc:
                    physician_key = product.physician if product.physician else None
                    if physician_key not in ingredients_by_physician:
                        ingredients_by_physician[physician_key] = []
                    if ingredient not in ingredients_by_physician[physician_key]:
                        ingredients_by_physician[physician_key].append(ingredient)
        
        # Sort physicians by name, with unassigned at the end
        sorted_physicians = sorted(
            ingredients_by_physician.keys(),
            key=lambda p: (p is None, p.name if p else "")
        )
        
        # Get ALL upcoming visits, not just the first one
        upcoming_visits = (
            PhysicianVisit.query.filter(PhysicianVisit.visit_date >= utcnow())
            .order_by(PhysicianVisit.visit_date)
            .all()
        )
        
        # Keep the first visit for backward compatibility with templates
        upcoming_visit = upcoming_visits[0] if upcoming_visits else None

        low_inventory = []
        gap_coverage_by_visit = []  # List of dicts: {visit: visit_obj, ingredients: [ing1, ing2]}
        
        # Check for low inventory
        for ingredient in ingredients:
            if ingredient.total_inventory_count < ingredient.min_threshold:
                low_inventory.append(ingredient)
        
        # Check for gap coverage needs for each upcoming visit
        if upcoming_visits:
            for visit in upcoming_visits:
                visit_gap_ingredients = []
                
                for ingredient in ingredients:
                    # Check if ingredient has products for this physician
                    has_physician_product = any(
                        product.physician_id == visit.physician_id 
                        for product in ingredient.products 
                        if not product.is_otc
                    )
                    
                    if has_physician_product and ingredient.depletion_date:
                        # Check if ingredient will run out before this visit
                        if ensure_timezone_utc(ingredient.depletion_date) < ensure_timezone_utc(visit.visit_date):
                            visit_gap_ingredients.append(ingredient)
                
                # Only add visits that have gap coverage needs
                if visit_gap_ingredients:
                    gap_coverage_by_visit.append({
                        'visit': visit,
                        'ingredients': visit_gap_ingredients
                    })

        return render_template(
            "index.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            ingredients=ingredients,
            ingredients_by_physician=ingredients_by_physician,
            sorted_physicians=sorted_physicians,
            otc_ingredients=otc_ingredients,
            upcoming_visit=upcoming_visit,
            low_inventory=low_inventory,
            gap_coverage_by_visit=gap_coverage_by_visit,
        )

    # Handle 404 errors
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors with a custom page."""
        logger.warning(f"Page not found: {request.path}")
        return render_template("404.html"), 404

    # Add scheduler tasks
    with app.app_context():
        # Register the enhanced auto-deduction task
        # We check for the enhanced version first, and fall back if not available
        try:
            # Try to import the new enhanced deduction service
            from deduction_service import perform_deductions

            # Use the enhanced version
            logger.info("Registering enhanced auto-deduction service")
            scheduler.add_task(
                name="auto_deduction",
                func=perform_deductions,
                interval_seconds=3600,  # 1 hour
            )
        except ImportError:
            # Fall back to the legacy auto-deduction method
            logger.warning(
                "Enhanced deduction service not available, using legacy auto-deduction"
            )
            from physician_visit_utils import auto_deduct_inventory

            scheduler.add_task(
                name="auto_deduction",
                func=auto_deduct_inventory,
                interval_seconds=3600,  # 1 hour
            )

        # Add task to check for upcoming visits (every 12 hours)
        scheduler.add_task(
            name="check_upcoming_visits",
            func=check_upcoming_visits,
            interval_seconds=43200,  # 12 hours
        )

        logger.info("Scheduled background tasks registered")

    return app


# Create the application instance for Gunicorn (lazy initialization)
app = None

def get_app():
    """Get or create the application instance."""
    global app
    if app is None:
        app = create_app()
        # Fix existing data in the database if needed
        fix_database_timezones(app)
    return app

# Application entry point for development
if __name__ == "__main__":
    # Get logger
    logger = logging.getLogger(__name__)
    
    # Get the app instance
    app = get_app()

    # Start the application
    port = int(os.environ.get("PORT", 8087))
    logger.info(f"Starting Medication Tracker on port {port}")
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])