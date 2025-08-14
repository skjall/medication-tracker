#!/bin/bash

# Script to download latest translations from Crowdin
# This is used to keep local translation files in sync with Crowdin

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📥 Updating translation files from Crowdin...${NC}"

# Change to script directory then to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

# Check if CROWDIN_API_TOKEN is set
if [ -z "$CROWDIN_API_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Warning: CROWDIN_API_TOKEN not set${NC}"
    echo "Please set your API token:"
    echo "  export CROWDIN_API_TOKEN=your_token_here"
    exit 1
fi

# Check if crowdin CLI is installed
if ! command -v crowdin &> /dev/null; then
    echo -e "${RED}❌ Error: Crowdin CLI not found${NC}"
    echo "Please install the Crowdin CLI:"
    echo "  macOS:  brew install crowdin"
    echo "  Linux:  npm install -g @crowdin/cli"
    echo "  Or see: https://developer.crowdin.com/cli-tool/"
    exit 1
fi

# Check if crowdin.yml exists
if [ ! -f "crowdin.yml" ]; then
    echo -e "${RED}❌ Error: crowdin.yml not found${NC}"
    echo "Please ensure you're running this script from the project root"
    exit 1
fi

echo "Downloading translations..."

# Download translations
# --no-progress: Don't show progress bar
# --skip-untranslated-strings: Don't include untranslated strings
# --skip-untranslated-files: Don't create files with no translations
if crowdin download \
    --no-progress \
    --skip-untranslated-strings \
    --skip-untranslated-files; then
    
    echo -e "${GREEN}✅ Translations downloaded successfully${NC}"
    
    # Show what was downloaded
    echo -e "\n${GREEN}📝 Translation files:${NC}"
    find translations -name "*.po" -type f | while read -r file; do
        # Get file size and last modified date
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            SIZE=$(stat -f%z "$file" | numfmt --to=iec-i --suffix=B 2>/dev/null || stat -f%z "$file")
            MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$file")
        else
            # Linux
            SIZE=$(stat --printf="%s" "$file" | numfmt --to=iec-i --suffix=B 2>/dev/null || stat --printf="%s" "$file")
            MODIFIED=$(stat --printf="%y" "$file" | cut -d' ' -f1,2 | cut -d'.' -f1)
        fi
        
        # Extract language code from path
        LANG=$(echo "$file" | sed -n 's/.*\/\([^\/]*\)\/LC_MESSAGES.*/\1/p')
        
        printf "  • %-10s %-40s %10s  %s\n" "[$LANG]" "$file" "$SIZE" "$MODIFIED"
    done
    
    # Compile translations
    echo -e "\n${GREEN}🔨 Compiling translations...${NC}"
    cd app
    pybabel compile -d ../translations
    cd ..
    
    echo -e "${GREEN}✅ Translations compiled successfully${NC}"
    
    # Show statistics
    echo -e "\n${GREEN}📊 Translation Statistics:${NC}"
    for po_file in translations/*/LC_MESSAGES/messages.po; do
        if [ -f "$po_file" ]; then
            LANG=$(basename $(dirname $(dirname "$po_file")))
            TRANSLATED=$(msgfmt --statistics "$po_file" 2>&1 | grep -oE '[0-9]+ translated' | grep -oE '[0-9]+' || echo "0")
            FUZZY=$(msgfmt --statistics "$po_file" 2>&1 | grep -oE '[0-9]+ fuzzy' | grep -oE '[0-9]+' || echo "0")
            UNTRANSLATED=$(msgfmt --statistics "$po_file" 2>&1 | grep -oE '[0-9]+ untranslated' | grep -oE '[0-9]+' || echo "0")
            
            TOTAL=$((TRANSLATED + FUZZY + UNTRANSLATED))
            if [ $TOTAL -gt 0 ]; then
                PERCENT=$((TRANSLATED * 100 / TOTAL))
                printf "  • %-5s: %3d%% translated (%d/%d strings)" "$LANG" "$PERCENT" "$TRANSLATED" "$TOTAL"
                
                if [ $FUZZY -gt 0 ]; then
                    printf ", %d fuzzy" "$FUZZY"
                fi
                if [ $UNTRANSLATED -gt 0 ]; then
                    printf ", %d untranslated" "$UNTRANSLATED"
                fi
                echo
            fi
        fi
    done
    
else
    echo -e "${RED}❌ Error: Failed to download translations${NC}"
    echo "Please check your CROWDIN_API_TOKEN and internet connection"
    exit 1
fi

echo -e "\n${GREEN}✨ Done! Translation files are up to date.${NC}"