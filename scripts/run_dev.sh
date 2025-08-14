#!/bin/bash

# Exit on error
set -e

echo "=== Development Environment Startup Script ==="
echo ""

# Extract source strings from the codebase
echo "📤 Extracting source strings..."
cd app && pybabel extract -F ../babel.cfg -k _l -k _ -k _n:1,2 -o ../translations/messages.pot . \
    --add-comments="TRANSLATORS:" --sort-by-file && cd ..
echo "✅ Source strings extracted to messages.pot"

# Upload source strings to Crowdin
echo "📤 Uploading source strings to Crowdin..."
crowdin upload sources --verbose || echo "⚠️  Crowdin upload failed or not configured. Continuing..."

# Download German translations from Crowdin
echo "📥 Downloading German translations from Crowdin..."
crowdin download -l de --verbose || echo "⚠️  Crowdin download failed or not configured. Continuing with local translations..."

echo ""
echo "🔨 Stopping existing containers..."
docker-compose -f docker-compose.dev.yml down

echo ""
echo "🚀 Building and starting development container..."
clear
docker-compose -f docker-compose.dev.yml up --build