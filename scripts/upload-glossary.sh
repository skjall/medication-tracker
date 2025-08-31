#!/bin/bash

# Crowdin Glossary Upload Script
# This script uploads the crowdin-glossary.csv file to Crowdin using the API

set -e

echo "📚 Crowdin Glossary Upload (API-based)"
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with CROWDIN_API_TOKEN and CROWDIN_PROJECT_ID"
    exit 1
fi

# Load environment variables
source .env

# Check for required environment variables
if [ -z "$CROWDIN_API_TOKEN" ] || [ -z "$CROWDIN_PROJECT_ID" ]; then
    echo "❌ Missing required environment variables in .env:"
    echo "   CROWDIN_API_TOKEN"
    echo "   CROWDIN_PROJECT_ID"
    exit 1
fi

echo "✅ Crowdin credentials loaded"
echo "   Project ID: $CROWDIN_PROJECT_ID"
echo "   API Token: ${CROWDIN_API_TOKEN:0:12}..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install it first"
    exit 1
fi

# Check if required Python packages are installed
python3 -c "import requests, dotenv" 2>/dev/null || {
    echo "📦 Installing required Python packages..."
    pip install requests python-dotenv
}

# Check if glossary file exists
if [ ! -f crowdin-glossary.csv ]; then
    echo "❌ crowdin-glossary.csv not found"
    exit 1
fi

# Get file size and line count for info
FILE_SIZE=$(stat -f%z crowdin-glossary.csv 2>/dev/null || stat -c%s crowdin-glossary.csv 2>/dev/null || echo "unknown")
LINE_COUNT=$(wc -l < crowdin-glossary.csv | tr -d ' ')
TERM_COUNT=$((LINE_COUNT - 1))  # Subtract header line

echo ""
echo "📊 Glossary information:"
echo "   Terms:      $TERM_COUNT medical/technical terms"
echo "   Format: Enriched CSV with full metadata"
echo "   File size:    $FILE_SIZE bytes"

echo ""
echo "🔍 Target glossary ID: 612724"
echo ""

# Run the Python script to manage the glossary
if python3 scripts/manage-glossary-api.py; then
    echo ""
    echo "🎉 Glossary upload successful!"
    echo "================================="
    echo ""
    echo "✅ Uploaded      $TERM_COUNT comprehensive medical/technical terms"
    echo "📚 Includes:"
    echo "   • Core terms: Medication, Inventory, Physician, Visit"
    echo "   • System features: Dashboard, Settings, Backup, Export"
    echo "   • Medical concepts: Dosage, Schedule, Prescription, Compliance"
    echo "   • German pharmacy: N1, N2, N3 package sizes"
    echo "   • UI/UX terms: Alert, Active, Inactive, Manual Entry"
    echo "   • Advanced: Side Effects, Contraindications, Generic, Brand Name"
    echo ""
    echo "🌍 Rich metadata provided:"
    echo "   • Part of speech for proper grammar"
    echo "   • Concept definitions and subjects"
    echo "   • Translation notes with German examples"
    echo "   • Translatable flags (N1/N2/N3 marked as non-translatable)"
    echo ""
    echo "Next steps for translators:"
    echo "1. 🔍 Glossary terms will be highlighted in source strings"
    echo "2. 💡 Context-aware suggestions during translation"
    echo "3. ✅ Consistent terminology across all translations"
    echo "4. 📖 Reference notes for German-specific terms"
    echo ""
    echo "Monitor and manage:"
    echo "- View in Crowdin: https://crowdin.com/project/$CROWDIN_PROJECT_ID/glossary"
    echo "- Update glossary: ./scripts/upload-glossary.sh"
    echo "- Direct API management: python3 scripts/manage-glossary-api.py"
else
    echo ""
    echo "❌ Glossary upload failed"
    echo ""
    echo "Common issues:"
    echo "1. Check your CROWDIN_API_TOKEN in .env"
    echo "2. Verify glossary ID 612724 exists"
    echo "3. Ensure CSV format is correct"
    echo "4. Check Crowdin API limits"
    echo ""
    echo "For detailed debug output, run:"
    echo "python3 scripts/manage-glossary-api.py"
    exit 1
fi