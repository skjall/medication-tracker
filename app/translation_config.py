"""
Translation and internationalization configuration module.
"""

import os
import logging
from flask import request, session
from flask_babel import Babel, gettext, ngettext

logger = logging.getLogger(__name__)


def discover_languages(app):
    """Dynamically discover available languages from translations directory."""
    languages = {"en": "English"}  # Always include English

    # Language name mapping
    language_names = {
        "de": "Deutsch",
        "es": "Español",
        "fr": "Français",
        "it": "Italiano",
        "pt": "Português",
        "nl": "Nederlands",
        "pl": "Polski",
        "ru": "Русский",
        "ja": "日本語",
        "zh": "中文",
        "ko": "한국어",
        "ar": "العربية",
        "hi": "हिन्दी",
        "tr": "Türkçe",
        "sv": "Svenska",
        "da": "Dansk",
        "no": "Norsk",
        "fi": "Suomi",
        "cs": "Čeština",
        "sk": "Slovenčina",
        "hu": "Magyar",
        "ro": "Română",
        "bg": "Български",
        "hr": "Hrvatski",
        "sl": "Slovenščina",
        "et": "Eesti",
        "lv": "Latviešu",
        "lt": "Lietuvių",
        "uk": "Українська",
        "he": "עברית",
        "th": "ไทย",
        "vi": "Tiếng Việt",
        "id": "Bahasa Indonesia",
        "ms": "Bahasa Melayu",
        "tl": "Filipino",
    }

    # Check if running in Docker
    if os.path.exists("/app/translations"):
        translations_dir = "/app/translations"
    else:
        translations_dir = os.path.join(
            os.path.dirname(app.root_path), "translations"
        )

    # Scan translations directory for language folders
    if os.path.exists(translations_dir):
        for item in os.listdir(translations_dir):
            lang_path = os.path.join(translations_dir, item)

            # Check if it's a valid language directory (2-letter code, not pot files)
            if (
                os.path.isdir(lang_path)
                and item != "en"  # Skip English (already included)
                and len(item) == 2
            ):  # Two-letter language codes

                # Check for messages.po file to confirm this is a valid language
                lc_messages_dir = os.path.join(lang_path, "LC_MESSAGES")
                messages_po = os.path.join(lc_messages_dir, "messages.po")
                if os.path.exists(messages_po):
                    # Use mapped name or fallback to code
                    language_name = language_names.get(item, item.upper())
                    languages[item] = language_name
                    logger.debug(
                        f"Discovered language: {item} ({language_name})"
                    )

    return languages


def calculate_translation_coverage(language_code, translations_dir):
    """Calculate translation coverage percentage across all domains for a language."""
    if language_code == "en":
        return 1.0  # English is always 100%

    try:
        import babel.messages.pofile as pofile

        total_translated = 0
        total_strings = 0

        # Get all domain .po files for this language
        lang_dir = os.path.join(translations_dir, language_code, "LC_MESSAGES")
        if not os.path.exists(lang_dir):
            return 0.0

        # Process each domain .po file
        po_files = [f for f in os.listdir(lang_dir) if f.endswith(".po")]
        if not po_files:
            return 0.0

        for po_file in po_files:
            po_path = os.path.join(lang_dir, po_file)

            try:
                with open(po_path, "r", encoding="utf-8") as f:
                    catalog = pofile.read_po(f)

                if len(catalog) > 0:
                    # Count non-empty translations (excluding header)
                    domain_translated = len(
                        [msg for msg in catalog if msg.id and msg.string]
                    )
                    domain_total = len(
                        [msg for msg in catalog if msg.id]
                    )  # Exclude header

                    total_translated += domain_translated
                    total_strings += domain_total

                    logger.debug(
                        f"Domain {po_file}: {domain_translated}/{domain_total} translated"
                    )

            except Exception as e:
                logger.debug(f"Error reading {po_file}: {e}")
                continue

        if total_strings == 0:
            return 0.0

        coverage = total_translated / total_strings
        logger.debug(
            f"Overall coverage for {language_code}: {total_translated}/{total_strings} = {coverage:.1%}"
        )
        return coverage

    except Exception as e:
        logger.warning(
            f"Could not calculate domain-based coverage for {language_code}: {e}"
        )
        return 0.0


def get_available_languages(app):
    """Return only languages with >80% translation coverage."""
    available = {}
    coverage_threshold = 0.8
    # Check if running in Docker
    if os.path.exists("/app/translations"):
        translations_dir = "/app/translations"
    else:
        translations_dir = os.path.join(
            os.path.dirname(app.root_path), "translations"
        )

    # Get current languages (dynamically discovered)
    all_languages = app.config["LANGUAGES"]
    logger.debug(f"All discovered languages: {list(all_languages.keys())}")

    for code, name in all_languages.items():
        if code == "en":  # Always show English
            available[code] = name
            logger.debug(
                f"Language {code} ({name}): Always available (base language)"
            )
            continue

        coverage = calculate_translation_coverage(code, translations_dir)
        logger.debug(f"Language {code} ({name}) coverage: {coverage:.1%}")

        if coverage >= coverage_threshold:
            available[code] = name
            logger.debug(
                f"Language {code} ({name}): AVAILABLE - {coverage:.1%} >= {coverage_threshold:.0%}"
            )
        else:
            logger.debug(
                f"Language {code} ({name}): HIDDEN - {coverage:.1%} < {coverage_threshold:.0%}"
            )

    logger.debug(
        f"Available languages for navigation: {list(available.keys())}"
    )
    return available


def get_translations_dir(app):
    """Return the correct translations directory (Docker vs local)."""
    # Prefer explicit env var if set
    env_dir = os.environ.get("BABEL_TRANSLATION_DIRECTORIES")
    if env_dir and os.path.exists(env_dir):
        return env_dir

    # Docker default
    docker_dir = "/app/translations"
    if os.path.exists(docker_dir):
        return docker_dir

    # Local dev fallback (next to project root)
    return os.path.join(app.root_path, "translations")


def setup_babel(app):
    """Configure and initialize Babel for internationalization."""
    translations_dir = get_translations_dir(app)

    # Debug: Check if translations directory exists
    logger.debug(f"App root path: {app.root_path}")
    logger.debug(f"Translations directory path: {translations_dir}")
    logger.debug(
        f"Translations directory exists: {os.path.exists(translations_dir)}"
    )

    # Configure languages dynamically
    app.config["LANGUAGES"] = discover_languages(app)
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = translations_dir

    def get_locale():
        # 1. Check URL parameter
        if request.args.get("lang"):
            session["language"] = request.args.get("lang")
            logger.debug(
                f"Locale set from URL parameter: {session['language']}"
            )

        # 2. Check user session
        if (
            "language" in session
            and session["language"] in app.config["LANGUAGES"]
        ):
            logger.debug(f"Using session language: {session['language']}")
            return session["language"]

        # 3. Use browser's preferred language
        browser_lang = (
            request.accept_languages.best_match(app.config["LANGUAGES"].keys())
            or "en"
        )
        logger.debug(f"Using browser language fallback: {browser_lang}")
        return browser_lang

    # Configure Babel to use the translations directory BEFORE initializing
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = translations_dir

    # Initialize Babel for i18n support with locale selector
    babel = Babel()
    babel.init_app(app, locale_selector=get_locale)

    # Explicitly register translation functions in Jinja2
    app.jinja_env.globals.update(_=gettext, _n=ngettext, get_locale=get_locale)

    # Debug logging
    if os.path.exists(translations_dir):
        logger.debug(
            f"Translations directory contents: {os.listdir(translations_dir)}"
        )
        de_dir = os.path.join(translations_dir, "de", "LC_MESSAGES")
        if os.path.exists(de_dir):
            logger.debug(
                f"German translations directory contents: {os.listdir(de_dir)}"
            )
            mo_file = os.path.join(de_dir, "messages.mo")
            logger.debug(f"German .mo file exists: {os.path.exists(mo_file)}")

    logger.debug(
        f"Babel translation directories: {app.config.get('BABEL_TRANSLATION_DIRECTORIES')}"
    )

    return babel


def register_translation_routes(app):
    """Register language switching and debug routes."""
    from flask import redirect, url_for, jsonify

    @app.route("/set_language/<language>")
    def set_language(language=None):
        session["language"] = language
        return redirect(request.referrer or url_for("index"))

    # Debug route for translation coverage (admin use)
    @app.route("/debug/translation-coverage")
    def debug_translation_coverage():
        # Check if running in Docker
        if os.path.exists("/app/translations"):
            translations_dir = "/app/translations"
        else:
            translations_dir = os.path.join(
                os.path.dirname(app.root_path), "translations"
            )
        coverage_data = {}

        for code, name in app.config["LANGUAGES"].items():
            coverage = calculate_translation_coverage(code, translations_dir)
            coverage_data[code] = {
                "name": name,
                "coverage": round(coverage * 100, 1),
                "available": coverage >= 0.8 or code == "en",
            }

        return jsonify(
            {
                "languages": coverage_data,
                "threshold": 80,
                "available_in_nav": list(get_available_languages(app).keys()),
            }
        )

    # Make available in templates
    @app.context_processor
    def inject_conf_vars():
        from flask_babel import get_locale

        current_locale = str(get_locale())
        return {
            "LANGUAGES": get_available_languages(
                app
            ),  # Only show available languages
            "ALL_LANGUAGES": app.config[
                "LANGUAGES"
            ],  # All configured languages for admin
            "CURRENT_LANGUAGE": current_locale,
        }
