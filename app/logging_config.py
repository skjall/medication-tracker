"""
Enhanced logging configuration for the Medication Tracker application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Any


def configure_logging(app_instance: Any) -> logging.Logger:
    """
    Configure enhanced logging for the application.

    Args:
        app_instance: The Flask application instance

    Returns:
        The configured root logger
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app_instance.root_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Log file paths
    main_log_file = os.path.join(logs_dir, "medication_tracker.log")
    error_log_file = os.path.join(logs_dir, "errors.log")
    debug_log_file = os.path.join(logs_dir, "debug.log")

    # Get log level from config or environment, default to INFO
    log_level_name = app_instance.config.get(
        "LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO")
    )
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicates when reloading in debug mode
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # Create formatters
    verbose_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s"
    )
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    error_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s"
    )

    # Main file handler (rotating log files)
    file_handler = RotatingFileHandler(
        main_log_file, maxBytes=10485760, backupCount=10  # 10MB
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(verbose_formatter)

    # Error file handler (only ERROR and CRITICAL)
    error_handler = RotatingFileHandler(
        error_log_file, maxBytes=10485760, backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(error_formatter)

    # Debug file handler (verbose, includes all logs at DEBUG level)
    debug_handler = RotatingFileHandler(
        debug_log_file, maxBytes=10485760, backupCount=3
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(verbose_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(console_handler)

    # Flask logger
    app_instance.logger.setLevel(log_level)

    # Log application startup
    app_instance.logger.info(
        f"Medication Tracker application starting with log level: {log_level_name}"
    )
    app_instance.logger.info(f"Main log file: {main_log_file}")
    app_instance.logger.info(f"Error log file: {error_log_file}")
    app_instance.logger.info(f"Debug log file: {debug_log_file}")

    # Create module loggers for key components
    timezone_logger = logging.getLogger("timezone_helper")
    timezone_logger.setLevel(log_level)
    timezone_logger.info("Timezone helper logger initialized")

    routes_logger = logging.getLogger("routes")
    routes_logger.setLevel(log_level)
    routes_logger.info("Routes logger initialized")

    models_logger = logging.getLogger("models")
    models_logger.setLevel(log_level)
    models_logger.info("Models logger initialized")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with the application's configuration.

    Args:
        name: Name of the logger

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Ensure it has at least one handler, or it will use the root logger's handlers
    if not logger.handlers and not logger.propagate:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(console_handler)

    return logger
