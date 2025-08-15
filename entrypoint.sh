#!/bin/bash
set -e

echo "Starting Medication Tracker..."

# Ensure data and log directories exist with proper permissions
mkdir -p /app/data /app/logs
chmod -R 777 /app/data /app/logs

# Clean up any stale migration locks from previous runs
if [ -f /app/data/migration.lock ]; then
    echo "Removing stale migration lock..."
    rm -f /app/data/migration.lock
fi
if [ -f /app/data/.migration_lock ]; then
    echo "Removing stale migration lock..."
    rm -f /app/data/.migration_lock
fi

# Create the application instance once
# This prevents multiple initializations and migration lock issues
echo "Starting gunicorn server..."
exec gunicorn --bind 0.0.0.0:8087 --workers 1 --threads 4 --timeout 120 --preload "main:app"