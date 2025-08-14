#!/bin/bash

# Exit on error
set -e

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

echo "=== Development Environment Startup Script ==="
echo "📁 Working directory: $PROJECT_ROOT"
echo ""

# Generate cache bust value to force fresh translation downloads
export CACHE_BUST=$(date +%s)

# Load .env file from project root if it exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading environment variables from $ENV_FILE..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)

    if [ -n "$CROWDIN_API_TOKEN" ] && [ -n "$CROWDIN_PROJECT_ID" ]; then
        echo "✅ Crowdin credentials found - translations will be synced during build"
        echo "   Project ID: ${CROWDIN_PROJECT_ID}"
        echo "   Token (first 5 chars): ${CROWDIN_API_TOKEN:0:5}..."
        echo "   Token length: ${#CROWDIN_API_TOKEN}"
        echo "   Cache bust: ${CACHE_BUST} (forces fresh download)"
    else
        echo "⚠️  Missing CROWDIN_API_TOKEN or CROWDIN_PROJECT_ID in .env - using local translations only"
        [ -z "$CROWDIN_API_TOKEN" ] && echo "   - CROWDIN_API_TOKEN not set"
        [ -z "$CROWDIN_PROJECT_ID" ] && echo "   - CROWDIN_PROJECT_ID not set"
    fi
else
    echo "⚠️  No .env file found at $ENV_FILE - using local translations only"
    echo "   Please create a .env file in the project root with:"
    echo "   CROWDIN_API_TOKEN=your_token_here"
    echo "   CROWDIN_PROJECT_ID=medication-tracker"
fi

echo ""
echo "🔨 Stopping existing containers..."
docker-compose -f docker-compose.dev.yml down

echo ""
echo "🚀 Building and starting development container..."
echo "   This will:"
echo "   - Extract strings from source code"
if [ -n "$CROWDIN_API_TOKEN" ]; then
    echo "   - Upload strings to Crowdin"
    echo "   - Download latest translations from Crowdin"
fi
echo "   - Compile translations"
echo ""

# Show build progress without clearing screen for debugging
echo "Starting Docker build with detailed output..."
docker-compose -f docker-compose.dev.yml build

echo ""
echo "Starting container..."
docker-compose -f docker-compose.dev.yml up