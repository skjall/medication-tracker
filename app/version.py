"""
Version information for the Medication Tracker application.
This file is auto-updated during the build process.
"""

# Standard library imports
import logging
import os

# Create a logger for this module
logger = logging.getLogger(__name__)

# Default fallback version in case the VERSION env var is not set
VERSION = "0.0.0"

# Check for environment variable (set during Docker build)
if "VERSION" in os.environ:
    VERSION = os.environ["VERSION"]


def get_version():
    """
    Returns the current application version.

    Returns:
        str: The version string
    """
    logger.debug(f"Current application version: {VERSION}")
    return VERSION
