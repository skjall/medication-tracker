"""
Logging configuration for the Medication Tracker application.

This module provides centralized configuration for application logging,
including file and console handlers.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any


def configure_logging(app_instance: Any) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        app_instance: The Flask application instance

    Returns:
        The configured root logger
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app_instance.root_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Log file path
    log_file = os.path.join(logs_dir, "medication_tracker.log")

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

    # File handler (rotating log files)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=10  # 10MB
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(verbose_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Flask logger
    app_instance.logger.setLevel(log_level)

    # Log application startup
    app_instance.logger.info(
        f"Medication Tracker application starting with log level: {log_level_name}"
    )
    app_instance.logger.info(f"Log file: {log_file}")

    return root_logger
