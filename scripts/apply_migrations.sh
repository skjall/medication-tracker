#!/bin/bash
# Script to apply database migrations
# Usage: ./scripts/apply_migrations.sh

set -e

# Navigate to the app directory
cd "$(dirname "$0")/../app"

# Apply the migrations
echo "Applying database migrations..."
python migration_cli.py apply

echo "Migrations applied successfully."