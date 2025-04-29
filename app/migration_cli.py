"""
Command-line interface for database migrations.

This module provides a CLI tool for managing database migrations,
including creating new migration scripts and applying them.
"""

# Standard library imports
import argparse
import logging
import os
import sys
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migration_cli")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Database Migration CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")

    # Apply migrations command
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument("--revision", help="Target revision (default: head)", default="head")

    # Show history command
    history_parser = subparsers.add_parser("history", help="Show migration history")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check if migrations are needed")

    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize migration environment")

    return parser.parse_args()


def run_cli() -> None:
    """
    Run the CLI tool with the provided arguments.
    """
    args = parse_args()

    # Add the parent directory to path so we can import the app
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Import only when needed to avoid circular imports
    from main import create_app
    from migration_utils import (
        create_migration,
        get_migration_history,
        initialize_migrations,
        check_migrations_needed,
        run_migrations,
    )

    # Create app with Flask test config
    app = create_app({"TESTING": True})

    if args.command == "create":
        # Create a new migration
        success = create_migration(app, args.message)
        if not success:
            logger.error("Failed to create migration")
            sys.exit(1)

    elif args.command == "apply":
        # Apply migrations
        success = run_migrations(app)
        if not success:
            logger.error("Failed to apply migrations")
            sys.exit(1)

    elif args.command == "history":
        # Show migration history
        revisions = get_migration_history(app)
        if not revisions:
            logger.info("No migration history found")
        else:
            logger.info("Migration history:")
            for rev_id, timestamp, desc in revisions:
                logger.info(f"  {rev_id} - {timestamp} - {desc}")

    elif args.command == "check":
        # Check if migrations are needed
        needed = check_migrations_needed(app)
        if needed:
            logger.info("Database migrations are needed")
            sys.exit(1)  # Non-zero exit code if migrations needed
        else:
            logger.info("Database is up to date")

    elif args.command == "init":
        # Initialize migration environment
        success = initialize_migrations(app)
        if not success:
            logger.error("Failed to initialize migration environment")
            sys.exit(1)

    else:
        logger.error("No command specified")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()