#!/bin/bash

# Crowdin Priming Script
# This script initializes Crowdin with all 714 translatable strings

set -e  # Exit on any error

echo "🚀 Crowdin Priming Script"
echo "========================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with CROWDIN_PROJECT_ID and CROWDIN_API_TOKEN"
    echo "Example:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your Crowdin credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Verify credentials are set
if [ -z "$CROWDIN_PROJECT_ID" ] || [ -z "$CROWDIN_API_TOKEN" ]; then
    echo "❌ Error: Crowdin credentials not set"
    echo "Please set CROWDIN_PROJECT_ID and CROWDIN_API_TOKEN in .env file"
    exit 1
fi

echo "✅ Crowdin credentials loaded"
echo "   Project ID: $CROWDIN_PROJECT_ID"
echo "   API Token: ${CROWDIN_API_TOKEN:0:10}..."

# Step 1: Extract latest strings
echo
echo "📝 Step 1: Extracting translatable strings..."
cd app && pybabel extract -F ../babel.cfg -k _ -o ../translations/messages.pot .
cd ..

# Count strings
string_count=$(grep -c '^msgid ' translations/messages.pot)
echo "   Extracted $string_count translatable strings"

# Step 2: Test Crowdin connection
echo
echo "🔗 Step 2: Testing Crowdin connection..."
if crowdin --version > /dev/null 2>&1; then
    echo "   ✅ Crowdin CLI installed"
else
    echo "   ❌ Crowdin CLI not found"
    echo "   Install with: brew install crowdin"
    exit 1
fi

# Test project access
if crowdin status > /dev/null 2>&1; then
    echo "   ✅ Crowdin project accessible"
else
    echo "   ❌ Cannot access Crowdin project"
    echo "   Check your credentials and project ID"
    exit 1
fi

# Step 3: Upload source template
echo
echo "📤 Step 3: Uploading source template to Crowdin..."
crowdin upload sources --verbose

echo "   ✅ Source template uploaded successfully"

# Step 4: Show project status
echo
echo "📊 Step 4: Crowdin project status..."
crowdin status --verbose

# Step 5: Create initial translation files for configured languages
echo
echo "🌍 Step 5: Creating initial translation files..."

# Update existing translation files with new strings
echo "   Updating existing translation files..."
pybabel update -i translations/messages.pot -d translations

# Create .po files for missing languages if they don't exist
for lang in es fr; do
    lang_dir="translations/$lang/LC_MESSAGES"
    po_file="$lang_dir/messages.po"
    
    if [ ! -f "$po_file" ]; then
        echo "   Creating initial $lang translation file..."
        mkdir -p "$lang_dir"
        pybabel init -i translations/messages.pot -d translations -l "$lang"
    else
        echo "   ✅ $lang translation file exists"
    fi
done

# Step 6: Compile existing translations
echo
echo "🔧 Step 6: Compiling translations..."
pybabel compile -d translations

# Step 7: Show translation coverage
echo
echo "📈 Step 7: Translation coverage report..."
./scripts/translation-coverage.sh

echo
echo "🎉 Crowdin Priming Complete!"
echo "==============================="
echo
echo "Next steps:"
echo "1. 🌐 Visit your Crowdin project: https://crowdin.com/project/your-project"
echo "2. 👥 Invite translators or start translating"
echo "3. 📥 Download translations: crowdin download"
echo "4. 🔄 Sync regularly: crowdin upload sources && crowdin download"
echo
echo "Monitor progress:"
echo "- Run: ./scripts/translation-coverage.sh"
echo "- Check: ./scripts/crowdin-status.sh"
echo
echo "Happy translating! 🚀"