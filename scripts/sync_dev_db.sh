#!/bin/bash

# sync_dev_db.sh - Download database from Docker container for migration development
#
# This script:
# 1. Downloads the current database from the medication-tracker-dev Docker container
# 2. Stores it in the local data/ directory
# 3. Stamps it with the latest migration to mark it as up-to-date
# 4. Optionally creates a new migration file
#
# Usage:
#   ./scripts/sync_dev_db.sh                    # Just sync the database
#   ./scripts/sync_dev_db.sh "migration name"   # Sync and create new migration

set -e  # Exit on any error

CONTAINER_NAME="medication-tracker-dev"
LOCAL_DB_PATH="app/data/medication_tracker.db"
CONTAINER_DB_PATH="/app/data/medication_tracker.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Database Sync from Docker Container ===${NC}"

# Check if container is running
if ! docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Container '${CONTAINER_NAME}' is not running${NC}"
    echo "Please start the container first with: docker-compose up -d"
    exit 1
fi

# Create app/data directory if it doesn't exist
mkdir -p app/data

# Download database from container
echo -e "${BLUE}Downloading database from container...${NC}"
docker cp "${CONTAINER_NAME}:${CONTAINER_DB_PATH}" "${LOCAL_DB_PATH}"

if [ ! -f "${LOCAL_DB_PATH}" ]; then
    echo -e "${RED}Error: Failed to download database from container${NC}"
    exit 1
fi

echo -e "${GREEN}Database downloaded successfully${NC}"

# Check what version the downloaded database is at
echo -e "${BLUE}Checking downloaded database version...${NC}"
DB_VERSION=$(sqlite3 "${LOCAL_DB_PATH}" "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "No version found")
echo -e "${YELLOW}Downloaded database is at version: ${DB_VERSION}${NC}"

# Create new migration if requested
if [ -n "$1" ]; then
    MIGRATION_NAME="$1"
    echo -e "${BLUE}Creating new migration: ${MIGRATION_NAME}${NC}"

    alembic revision --autogenerate -m "${MIGRATION_NAME}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Migration created successfully${NC}"
        echo -e "${YELLOW}Please review the generated migration file before applying it${NC}"
    else
        echo -e "${RED}Error: Failed to create migration${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}=== Database sync complete ===${NC}"
echo -e "${YELLOW}Local database is now ready for migration development${NC}"

# Show some useful next steps
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  - Review your model changes"
if [ -n "$1" ]; then
    echo "  - Edit the generated migration file if needed"
    echo "  - Test the migration: alembic upgrade head"
else
    echo "  - Create migration: alembic revision --autogenerate -m 'description'"
fi
echo "  - Copy database back to container when ready: docker cp ${LOCAL_DB_PATH} ${CONTAINER_NAME}:${CONTAINER_DB_PATH}"