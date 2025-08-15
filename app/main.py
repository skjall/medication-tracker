"""
Main application module for the Medication Tracker application.
"""

# Standard library imports
import logging
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone  # noqa: E402
from typing import Any, Dict, Optional  # noqa: E402

# Third-party imports
from flask import Flask, render_template, request, session  # noqa: E402
from flask_babel import Babel, get_locale, gettext, ngettext  # noqa: E402

# Local application imports
from logging_config import configure_logging  # noqa: E402
from models import (  # noqa: E402
    db,
    utcnow,
    ensure_timezone_utc,
    Medication,
    PhysicianVisit,
    Order,
    Inventory,
    InventoryLog
)
from task_scheduler import TaskScheduler  # noqa: E402


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
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "dev"
        ),  # Use a secure key in production
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.root_path, 'data', 'medication_tracker.db')}",
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

    db.init_app(app)
    
    # Debug: Check if translations directory exists  
    translations_dir = os.path.join(os.path.dirname(app.root_path), 'translations')

    def discover_languages():
        """Dynamically discover available languages from translations directory."""
        languages = {'en': 'English'}  # Always include English
        
        # Language name mapping
        language_names = {
            'de': 'Deutsch',
            'es': 'Español', 
            'fr': 'Français',
            'it': 'Italiano',
            'pt': 'Português',
            'nl': 'Nederlands',
            'pl': 'Polski',
            'ru': 'Русский',
            'ja': '日本語',
            'zh': '中文',
            'ko': '한국어',
            'ar': 'العربية',
            'hi': 'हिन्दी',
            'tr': 'Türkçe',
            'sv': 'Svenska',
            'da': 'Dansk',
            'no': 'Norsk',
            'fi': 'Suomi',
            'cs': 'Čeština',
            'sk': 'Slovenčina',
            'hu': 'Magyar',
            'ro': 'Română',
            'bg': 'Български',
            'hr': 'Hrvatski',
            'sl': 'Slovenščina',
            'et': 'Eesti',
            'lv': 'Latviešu',
            'lt': 'Lietuvių',
            'uk': 'Українська',
            'he': 'עברית',
            'th': 'ไทย',
            'vi': 'Tiếng Việt',
            'id': 'Bahasa Indonesia',
            'ms': 'Bahasa Melayu',
            'tl': 'Filipino',
        }
        
        # Scan translations directory for language folders
        if os.path.exists(translations_dir):
            for item in os.listdir(translations_dir):
                lang_path = os.path.join(translations_dir, item)
                
                # Check if it's a valid language directory (2-letter code, not pot files)
                if (os.path.isdir(lang_path) and 
                    item != 'en' and  # Skip English (already included)
                    len(item) == 2):  # Two-letter language codes
                    
                    # Check for messages.po file to confirm this is a valid language
                    lc_messages_dir = os.path.join(lang_path, 'LC_MESSAGES')
                    messages_po = os.path.join(lc_messages_dir, 'messages.po')
                    if os.path.exists(messages_po):
                        # Use mapped name or fallback to code
                        language_name = language_names.get(item, item.upper())
                        languages[item] = language_name
                        logger.debug(f"Discovered language: {item} ({language_name})")
        
        return languages

    # Configure languages dynamically
    app.config['LANGUAGES'] = discover_languages()
    
    def get_locale():
        # 1. Check URL parameter
        if request.args.get('lang'):
            session['language'] = request.args.get('lang')
            logger.debug(f"Locale set from URL parameter: {session['language']}")
        
        # 2. Check user session
        if 'language' in session and session['language'] in app.config['LANGUAGES']:
            logger.debug(f"Using session language: {session['language']}")
            return session['language']
        
        # 3. Use browser's preferred language
        browser_lang = request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'
        logger.debug(f"Using browser language fallback: {browser_lang}")
        return browser_lang
    
    # Configure Babel to use the translations directory BEFORE initializing
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = translations_dir
    
    # Initialize Babel for i18n support with locale selector
    babel = Babel()
    babel.init_app(app, locale_selector=get_locale)
    
    # Explicitly register translation functions in Jinja2
    app.jinja_env.globals.update(_=gettext, _n=ngettext, get_locale=get_locale)
    
    logger.debug(f"App root path: {app.root_path}")
    logger.debug(f"Translations directory path: {translations_dir}")
    logger.debug(f"Translations directory exists: {os.path.exists(translations_dir)}")
    
    # Debug: List what's actually in the app directory
    logger.debug(f"Contents of app root path ({app.root_path}): {os.listdir(app.root_path) if os.path.exists(app.root_path) else 'Does not exist'}")
    parent_dir = os.path.dirname(app.root_path)
    logger.debug(f"Contents of parent directory ({parent_dir}): {os.listdir(parent_dir) if os.path.exists(parent_dir) else 'Does not exist'}")
    
    if os.path.exists(translations_dir):
        logger.debug(f"Translations directory contents: {os.listdir(translations_dir)}")
        de_dir = os.path.join(translations_dir, 'de', 'LC_MESSAGES')
        if os.path.exists(de_dir):
            logger.debug(f"German translations directory contents: {os.listdir(de_dir)}")
            mo_file = os.path.join(de_dir, 'messages.mo')
            logger.debug(f"German .mo file exists: {os.path.exists(mo_file)}")
    
    logger.debug(f"Babel translation directories: {app.config.get('BABEL_TRANSLATION_DIRECTORIES')}")

    # Set up the database URI for SQLAlchemy
    app.db = db

    # Initialize task scheduler
    scheduler = TaskScheduler(app)

    # Initialize database with migrations
    with app.app_context():
        # Import here to avoid circular imports
        from migration_utils import stamp_database_to_latest
        from sqlalchemy import inspect
        
        # Check if this is a fresh database (no tables exist)
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables or len(existing_tables) == 0:
            # Fresh database - create all tables directly
            logger.info("Fresh database detected - creating all tables")
            try:
                db.create_all()
                logger.info("Database tables created successfully")
                
                # Stamp database to latest migration to skip running them
                stamp_database_to_latest(app)
                logger.info("Database stamped to latest migration version")
                
                # Create default settings
                from models.settings import Settings
                if not Settings.query.first():
                    default_settings = Settings()
                    db.session.add(default_settings)
                    db.session.commit()
                    logger.info("Default settings created")
                    
            except Exception as e:
                logger.error(f"Error creating database tables: {e}")
                # Continue anyway - some tables might have been created
        elif 'alembic_version' not in existing_tables:
            # Database exists but no migration tracking - stamp to latest
            logger.info("Existing database without migration tracking - stamping to latest")
            stamp_database_to_latest(app)
        else:
            # Database exists with migration tracking
            # Skip migrations if:
            # 1. They were already run during startup (IS_STARTUP_MIGRATION set)
            # 2. We're in a Gunicorn worker process (detected by checking for master process)
            # 3. Migrations are explicitly disabled
            
            # Check if we're in a Gunicorn worker
            # Gunicorn sets SERVER_SOFTWARE environment variable
            is_gunicorn_worker = (
                'gunicorn' in os.environ.get('SERVER_SOFTWARE', '').lower() or
                'gunicorn' in sys.modules
            )
            
            # Only run migrations if not in a worker and not already done at startup
            if (not is_gunicorn_worker and 
                not os.environ.get('IS_STARTUP_MIGRATION') and 
                os.environ.get('RUN_MIGRATIONS') != 'false'):
                logger.info("Database already initialized with migration tracking - checking for pending migrations")
                from migration_utils import run_migrations_with_lock
                if run_migrations_with_lock(app):
                    logger.info("Migrations completed successfully")
                else:
                    logger.warning("Migration run failed or timed out - continuing anyway")
            else:
                reason = []
                if is_gunicorn_worker:
                    reason.append("Gunicorn worker")
                if os.environ.get('IS_STARTUP_MIGRATION'):
                    reason.append("startup migration completed")
                if os.environ.get('RUN_MIGRATIONS') == 'false':
                    reason.append("migrations disabled")
                logger.debug(f"Skipping migrations ({', '.join(reason)})")

    # Register blueprints (routes)
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

    # Add utility functions to Jinja
    from utils import min_value, make_aware, format_date, format_datetime, format_time, to_local_timezone

    app.jinja_env.globals.update(min=min_value)
    app.jinja_env.globals.update(make_aware=make_aware)
    app.jinja_env.globals.update(format_date=format_date)
    app.jinja_env.globals.update(format_datetime=format_datetime)
    app.jinja_env.globals.update(format_time=format_time)
    app.jinja_env.globals.update(to_local_timezone=to_local_timezone)

    # Context processor to add date/time variables to all templates
    @app.context_processor
    def inject_now():
        # Get UTC time first
        utc_now = utcnow()

        # Convert to local timezone
        from utils import to_local_timezone

        local_now = to_local_timezone(utc_now)

        # Get settings for access in all templates
        from models import Settings

        settings = Settings.get_settings()

        # Return both UTC and local time, plus settings
        return {
            "now": local_now,  # Local time for display
            "utc_now": utc_now,  # UTC time for backend calculations
            "settings": settings,  # Application settings for templates
        }

    def calculate_translation_coverage(language_code):
        """Calculate translation coverage percentage across all domains for a language."""
        if language_code == 'en':
            return 1.0  # English is always 100%
        
        try:
            import babel.messages.pofile as pofile
            
            total_translated = 0
            total_strings = 0
            
            # Get all domain .po files for this language
            lang_dir = os.path.join(translations_dir, language_code, 'LC_MESSAGES')
            if not os.path.exists(lang_dir):
                return 0.0
                
            # Process each domain .po file
            po_files = [f for f in os.listdir(lang_dir) if f.endswith('.po')]
            if not po_files:
                return 0.0
                
            for po_file in po_files:
                po_path = os.path.join(lang_dir, po_file)
                
                try:
                    with open(po_path, 'r', encoding='utf-8') as f:
                        catalog = pofile.read_po(f)
                    
                    if len(catalog) > 0:
                        # Count non-empty translations (excluding header)
                        domain_translated = len([msg for msg in catalog if msg.id and msg.string])
                        domain_total = len([msg for msg in catalog if msg.id])  # Exclude header
                        
                        total_translated += domain_translated
                        total_strings += domain_total
                        
                        logger.debug(f"Domain {po_file}: {domain_translated}/{domain_total} translated")
                        
                except Exception as e:
                    logger.debug(f"Error reading {po_file}: {e}")
                    continue
            
            if total_strings == 0:
                return 0.0
                
            coverage = total_translated / total_strings
            logger.debug(f"Overall coverage for {language_code}: {total_translated}/{total_strings} = {coverage:.1%}")
            return coverage
            
        except Exception as e:
            logger.warning(f"Could not calculate domain-based coverage for {language_code}: {e}")
            return 0.0

    def get_available_languages():
        """Return only languages with >80% translation coverage."""
        available = {}
        coverage_threshold = 0.8
        
        # Get current languages (dynamically discovered)
        all_languages = app.config['LANGUAGES']
        logger.debug(f"All discovered languages: {list(all_languages.keys())}")
        
        for code, name in all_languages.items():
            if code == 'en':  # Always show English
                available[code] = name
                logger.debug(f"Language {code} ({name}): Always available (base language)")
                continue
                
            coverage = calculate_translation_coverage(code)
            logger.debug(f"Language {code} ({name}) coverage: {coverage:.1%}")
            
            if coverage >= coverage_threshold:
                available[code] = name
                logger.debug(f"Language {code} ({name}): AVAILABLE - {coverage:.1%} >= {coverage_threshold:.0%}")
            else:
                logger.debug(f"Language {code} ({name}): HIDDEN - {coverage:.1%} < {coverage_threshold:.0%}")
        
        logger.debug(f"Available languages for navigation: {list(available.keys())}")
        return available

    # Language switching route
    @app.route('/set_language/<language>')
    def set_language(language=None):
        from flask import redirect, url_for
        session['language'] = language
        return redirect(request.referrer or url_for('index'))
    
    # Debug route for translation coverage (admin use)
    @app.route('/debug/translation-coverage')
    def debug_translation_coverage():
        from flask import jsonify
        coverage_data = {}
        
        for code, name in app.config['LANGUAGES'].items():
            coverage = calculate_translation_coverage(code)
            coverage_data[code] = {
                'name': name,
                'coverage': round(coverage * 100, 1),
                'available': coverage >= 0.8 or code == 'en'
            }
        
        return jsonify({
            'languages': coverage_data,
            'threshold': 80,
            'available_in_nav': list(get_available_languages().keys())
        })
    
    # Make available in templates
    @app.context_processor
    def inject_conf_vars():
        return {
            'LANGUAGES': get_available_languages(),  # Only show available languages
            'ALL_LANGUAGES': app.config['LANGUAGES'],  # All configured languages for admin
            'CURRENT_LANGUAGE': session.get('language', 'en')
        }
    
    # Add translation functions to template globals
    app.jinja_env.globals['_'] = gettext
    app.jinja_env.globals['_n'] = ngettext

    # Home route
    @app.route("/test_translation")
    def test_translation():
        return render_template("test_translation.html")
    
    @app.route("/")
    def index():
        """Render the dashboard/home page."""
        from flask_babel import get_locale
        current_locale = get_locale()
        logger.debug(f"Rendering dashboard page with locale: {current_locale}")
        logger.debug(f"Session data: {dict(session)}")
        logger.debug(f"URL args: {dict(request.args)}")
        
        # Test translation within request context
        from flask_babel import gettext
        test_translation = gettext('Dashboard')
        test_translation2 = gettext('No upcoming physician visits scheduled.')
        logger.debug(f"Translation test - 'Dashboard': '{test_translation}'")
        logger.debug(f"Translation test - 'No upcoming physician visits scheduled.': '{test_translation2}'")
        medications = Medication.query.order_by(Medication.name).all()
        
        # Group medications by physician or OTC status for display
        medications_by_physician = {}
        otc_medications = []
        
        for med in medications:
            if med.is_otc:
                otc_medications.append(med)
            else:
                physician_key = med.physician if med.physician else None
                if physician_key not in medications_by_physician:
                    medications_by_physician[physician_key] = []
                medications_by_physician[physician_key].append(med)
        
        # Sort physicians by name, with unassigned at the end
        sorted_physicians = sorted(
            medications_by_physician.keys(),
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
        gap_coverage_by_visit = []  # List of dicts: {visit: visit_obj, medications: [med1, med2]}
        
        for med in medications:
            if med.inventory and med.inventory.is_low:
                low_inventory.append(med)
        
        # Check for gap coverage needs for each upcoming visit
        if upcoming_visits:
            from utils import ensure_timezone_utc
            
            for visit in upcoming_visits:
                visit_gap_medications = []
                
                for med in medications:
                    if (med.inventory and med.depletion_date and 
                        not med.is_otc and  # Exclude OTC medications
                        med.physician_id == visit.physician_id):  # Only medications for this specific physician
                        # Check if medication will run out before this visit
                        if ensure_timezone_utc(med.depletion_date) < ensure_timezone_utc(visit.visit_date):
                            visit_gap_medications.append(med)
                
                # Only add visits that have gap coverage needs
                if visit_gap_medications:
                    gap_coverage_by_visit.append({
                        'visit': visit,
                        'medications': visit_gap_medications
                    })

        return render_template(
            "index.html",
            local_time=to_local_timezone(datetime.now(timezone.utc)),
            medications=medications,
            medications_by_physician=medications_by_physician,
            sorted_physicians=sorted_physicians,
            otc_medications=otc_medications,
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

    @app.template_filter("datetime")
    def parse_datetime(value):
        """Parse an ISO format datetime string into a datetime object."""
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            # If the string doesn't match ISO format, return current time as fallback
            return datetime.now(timezone.utc)

    return app


# Simple function to check upcoming visits and perform any necessary actions
def check_upcoming_visits():
    """Check upcoming visits and perform any necessary actions."""
    logger = logging.getLogger(__name__)
    logger.info("Checking upcoming visits")

    from models import PhysicianVisit, utcnow

    # Get visits in the next 7 days
    now = utcnow()
    one_week_later = now + timedelta(days=7)

    upcoming = (
        PhysicianVisit.query.filter(
            PhysicianVisit.visit_date >= now,
            PhysicianVisit.visit_date <= one_week_later,
        )
        .order_by(PhysicianVisit.visit_date)
        .all()
    )

    logger.info(f"Found {len(upcoming)} visits in the next 7 days")

    # This is where we could add code to send notifications
    # or perform other actions based on upcoming visits

    return len(upcoming)


# After database initialization, ensure all existing datetimes have timezone info
def fix_database_timezones(app):
    """
    Update existing database records to ensure all datetime fields have timezone info.
    This is a one-time fix for existing data.
    """
    with app.app_context():
        logger = logging.getLogger(__name__)
        logger.info("Running timezone fix for database records")

        try:
            # Fix PhysicianVisit dates
            visits = PhysicianVisit.query.all()
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
            logger.info("Successfully updated database with timezone information.")
        except Exception as e:
            logger.error(f"Error updating database timezones: {e}")
            db.session.rollback()


# Application entry point
if __name__ == "__main__":
    app = create_app()

    # Get logger
    logger = logging.getLogger(__name__)

    # Fix existing data in the database if needed
    fix_database_timezones(app)

    # Start the application
    port = int(os.environ.get("PORT", 8087))
    logger.info(f"Starting Medication Tracker on port {port}")
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
