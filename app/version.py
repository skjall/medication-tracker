"""
Version information for the Medication Tracker application.
This file is auto-updated during the build process.
"""

import os

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
    return VERSION
