"""
Route registration module for Flask blueprints.
"""

import logging

logger = logging.getLogger(__name__)


def register_blueprints(app):
    """Register all application blueprints."""
    from routes.physicians import physician_bp
    from routes.visits import visit_bp
    from routes.orders import order_bp
    from routes.settings import settings_bp
    from routes.schedule import schedule_bp
    from routes.system import system_bp
    from routes.scanner import bp as scanner_bp
    from routes.ingredients import ingredients_bp
    from routes.package_onboarding import bp as package_onboarding_bp
    from routes.pdf_mapper import bp as pdf_mapper_bp
    app.register_blueprint(physician_bp)
    app.register_blueprint(visit_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(ingredients_bp)
    app.register_blueprint(package_onboarding_bp)
    app.register_blueprint(pdf_mapper_bp)

    logger.info("All blueprints registered successfully")
