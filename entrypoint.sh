#!/bin/bash
set -e

echo "Starting Medication Tracker..."

# Ensure data and log directories exist with proper permissions
mkdir -p /app/data /app/logs
chmod -R 777 /app/data /app/logs

# Only run migrations with a single process
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Running database migrations..."
    
    # Use Python to run migrations directly with Alembic, not through the app
    python -c "
import os
import sys
os.chdir('/app')
from alembic import command
from alembic.config import Config

try:
    cfg = Config('alembic.ini')
    cfg.set_main_option('sqlalchemy.url', 'sqlite:////app/data/medication_tracker.db')
    command.upgrade(cfg, 'head')
    print('Migrations completed successfully')
except Exception as e:
    print(f'Migration failed: {e}')
    sys.exit(1)
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