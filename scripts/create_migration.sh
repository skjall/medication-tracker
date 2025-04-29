#!/bin/bash
# Script to create a new database migration
# Usage: ./scripts/create_migration.sh "Add new field to medications table"

set -e

# Check if message is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 \"Migration message\""
    exit 1
fi

MESSAGE="$1"

# Navigate to the app directory
cd "$(dirname "$0")/../app"

# Create the migration
echo "Creating migration: $MESSAGE"
python migration_cli.py create "$MESSAGE"

echo "Migration created successfully."
echo "Check the migrations/versions directory for the new migration file."