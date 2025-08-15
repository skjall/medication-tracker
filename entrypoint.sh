#!/bin/bash
set -e

echo "Starting Medication Tracker..."

# Ensure data and log directories exist with proper permissions
mkdir -p /app/data /app/logs
chmod -R 777 /app/data /app/logs

# Only run migrations with a single process
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Running database migrations..."
    python -c "
from main import create_app
from migration_utils import run_migrations_with_lock
import sys

app = create_app()
with app.app_context():
    if not run_migrations_with_lock(app):
        print('Migration failed!')
        sys.exit(1)
print('Migrations completed successfully')
"
    if [ $? -ne 0 ]; then
        echo "Migration failed, exiting..."
        exit 1
    fi
fi

# Start gunicorn with multiple workers
# Set environment variable so workers don't try to run migrations
export GUNICORN_WORKER=true
echo "Starting gunicorn server..."
exec gunicorn --bind 0.0.0.0:8087 --workers 4 --threads 2 --timeout 120 "main:create_app()"