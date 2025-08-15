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

# Run migrations before starting the app (if not disabled)
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Running database migrations..."
    
    # Use Python to run migrations with proper app context
    python -c "
import os
import sys
os.chdir('/app')

# Set environment to prevent worker migration attempts
os.environ['IS_STARTUP_MIGRATION'] = 'true'

from main import create_app
from migration_utils import run_migrations_with_lock

app = create_app()
with app.app_context():
    success = run_migrations_with_lock(app)
    if not success:
        print('Migration failed or timed out')
        sys.exit(1)
    print('Migrations completed successfully')
"
    if [ $? -ne 0 ]; then
        echo "Migration failed, exiting..."
        exit 1
    fi
fi

# Start gunicorn with multiple workers
# Use --preload to ensure all workers share the same app instance after migrations
echo "Starting gunicorn server..."
exec gunicorn --bind 0.0.0.0:8087 --workers 4 --threads 2 --timeout 120 --preload "main:create_app()"