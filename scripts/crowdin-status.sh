#!/bin/bash

# Crowdin Status Script
# Quick status check for Crowdin project

set -e

echo "📊 Crowdin Project Status"
echo "========================"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if credentials are available
if [ -z "$CROWDIN_PROJECT_ID" ] || [ -z "$CROWDIN_API_TOKEN" ]; then
    echo "❌ Crowdin credentials not found"
    echo "Please run: ./scripts/crowdin-prime.sh"
    exit 1
fi

echo "Project ID: $CROWDIN_PROJECT_ID"
echo

# Get project info
echo "📈 Translation Progress:"
echo "----------------------"
crowdin status

echo
echo "📁 Project Configuration:"
echo "------------------------"
crowdin config

echo
echo "🔄 Quick Actions:"
echo "----------------"
echo "Upload new strings:    crowdin upload sources"
echo "Download translations: crowdin download"
echo "Full sync:            crowdin upload sources && crowdin download"
echo "Local coverage:       ./scripts/translation-coverage.sh"