"""
Route registration module for Flask blueprints.
"""

import logging

logger = logging.getLogger(__name__)


def register_blueprints(app):
    """Register all application blueprints."""
    from routes.medications import medication_bp
    from routes.physicians import physician_bp
    from routes.inventory import inventory_bp
    from routes.visits import visit_bp
    from routes.orders import order_bp
    from routes.settings import settings_bp
    from routes.schedule import schedule_bp
    from routes.prescription_templates import prescription_bp
    from routes.system import system_bp
    from routes.scanner import bp as scanner_bp
    from routes.medication_packages import bp as medication_packages_bp

    app.register_blueprint(medication_bp)
    app.register_blueprint(physician_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(visit_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(prescription_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(medication_packages_bp)
    
    logger.info("All blueprints registered successfully")