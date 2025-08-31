#!/bin/bash

# Manage Translations for Crowdin Integration
# This script handles the complete workflow for translations

set -e

LANGUAGES="de"

show_help() {
    cat << EOF
Manage Translations for Medication Tracker

Usage: $0 <command> [options]

Commands:
  extract     Extract all translatable strings into messages.pot
  init        Initialize .po files for all languages
  update      Update existing .po files with new strings from messages.pot
  compile     Compile .po files to .mo files for all languages
  upload      Upload messages.pot to Crowdin
  download    Download translated .po files from Crowdin
  glossary    Upload medical/technical glossary to Crowdin
  status      Show translation coverage for all languages
  full        Run complete workflow: extract -> update -> compile

Options:
  -l, --lang LANG    Process only specific language (e.g., -l de)
  -h, --help         Show this help message

Examples:
  $0 extract                    # Extract all translatable strings
  $0 init -l de                 # Initialize German translation only
  $0 update                     # Update all existing translations
  $0 compile                    # Compile all translations
  $0 upload                     # Upload messages.pot to Crowdin
  $0 glossary                   # Upload medical/technical glossary to Crowdin
  $0 full                       # Complete workflow for development
EOF
}

extract_translations() {
    echo "🔄 Extracting translatable strings..."
    echo "======================================"

    cd app

    echo "  📱 Extracting all strings to messages.pot..."
    pybabel extract -F ../babel.cfg -k _l -k _ -k _n:1,2 -o ../translations/messages.pot . \
        --add-comments="TRANSLATORS:" --sort-by-file

    cd ..

    # Count extracted strings
    if [ -f "translations/messages.pot" ]; then
        count=$(grep -c '^msgid ' "translations/messages.pot" 2>/dev/null || echo "0")
        echo
        echo "📊 Extraction Summary:"
        echo "---------------------"
        echo "  Total strings: $count"
    fi

    echo
    echo "✅ String extraction complete!"
}

init_translations() {
    local target_lang="$1"

    echo "🌍 Initializing translation files..."
    echo "===================================="

    languages_to_process="$LANGUAGES"
    if [ -n "$target_lang" ]; then
        languages_to_process="$target_lang"
        echo "  Processing language: $target_lang"
    fi

    cd app

    for lang in $languages_to_process; do
        if [ -f "../translations/messages.pot" ]; then
            echo "  🔤 Initializing ${lang}/messages.po..."
            pybabel init -i ../translations/messages.pot -d ../translations -l "$lang" 2>/dev/null || {
                echo "    ℹ️  ${lang}/messages.po already exists (skipped)"
            }
        else
            echo "    ❌ Missing: translations/messages.pot"
            echo "    Run 'extract' command first"
            exit 1
        fi
    done

    cd ..

    echo
    echo "✅ Translation initialization complete!"
}

update_translations() {
    local target_lang="$1"

    echo "🔄 Updating existing translation files..."
    echo "========================================"

    languages_to_process="$LANGUAGES"
    if [ -n "$target_lang" ]; then
        languages_to_process="$target_lang"
        echo "  Processing language: $target_lang"
    fi

    cd app

    for lang in $languages_to_process; do
        po_file="../translations/${lang}/LC_MESSAGES/messages.po"
        pot_file="../translations/messages.pot"

        if [ -f "$po_file" ] && [ -f "$pot_file" ]; then
            echo "  🔄 Updating ${lang}/messages.po..."
            pybabel update -i "$pot_file" -d ../translations -l "$lang"
        elif [ ! -f "$po_file" ]; then
            echo "    ℹ️  ${lang}/messages.po doesn't exist - initializing..."
            pybabel init -i "$pot_file" -d ../translations -l "$lang"
        fi
    done

    cd ..

    echo
    echo "✅ Translation update complete!"
}

compile_translations() {
    local target_lang="$1"

    echo "⚙️  Compiling translation files..."
    echo "================================="

    languages_to_process="$LANGUAGES"
    if [ -n "$target_lang" ]; then
        languages_to_process="$target_lang"
        echo "  Processing language: $target_lang"
    fi

    cd app

    for lang in $languages_to_process; do
        po_file="../translations/${lang}/LC_MESSAGES/messages.po"

        if [ -f "$po_file" ]; then
            echo "  ⚙️  Compiling ${lang}/messages.mo..."
            pybabel compile -d ../translations -l "$lang"
        fi
    done

    cd ..

    echo
    echo "✅ Translation compilation complete!"
}

upload_to_crowdin() {
    echo "☁️  Uploading source file to Crowdin..."
    echo "======================================"

    # Check if Crowdin CLI is available
    if ! command -v crowdin &> /dev/null; then
        echo "❌ Crowdin CLI not found. Install with: npm install -g @crowdin/cli"
        exit 1
    fi

    # Check if .env contains required variables
    if [ ! -f ".env" ] || ! grep -q "CROWDIN_PROJECT_ID" .env || ! grep -q "CROWDIN_API_TOKEN" .env; then
        echo "❌ Missing Crowdin configuration in .env file"
        echo "   Required: CROWDIN_PROJECT_ID and CROWDIN_API_TOKEN"
        exit 1
    fi

    echo "  📤 Uploading messages.pot..."
    crowdin upload sources

    echo
    echo "✅ Upload to Crowdin complete!"
}

upload_glossary() {
    echo "📚 Uploading medical/technical glossary to Crowdin..."
    echo "===================================================="

    # Run the dedicated glossary upload script
    if [ -f "./scripts/upload-glossary.sh" ]; then
        ./scripts/upload-glossary.sh
    else
        echo "❌ Glossary upload script not found: ./scripts/upload-glossary.sh"
        exit 1
    fi
}

download_from_crowdin() {
    echo "☁️  Downloading translations from Crowdin..."
    echo "=========================================="

    # Check if Crowdin CLI is available
    if ! command -v crowdin &> /dev/null; then
        echo "❌ Crowdin CLI not found. Install with: npm install -g @crowdin/cli"
        exit 1
    fi

    echo "  📥 Downloading translated files..."
    crowdin download

    echo
    echo "  ⚙️  Compiling downloaded translations..."
    compile_translations

    echo
    echo "✅ Download from Crowdin complete!"
}

show_status() {
    echo "📊 Translation Status Report"
    echo "============================"

    pot_file="translations/messages.pot"
    if [ ! -f "$pot_file" ]; then
        echo "❌ messages.pot not found - run 'extract' first"
        exit 1
    fi

    total_strings=$(grep -c '^msgid ' "$pot_file" 2>/dev/null || echo "0")
    echo
    echo "Source file: messages.pot"
    echo "Total strings: $total_strings"
    echo

    echo "Language Coverage:"
    echo "-----------------"

    # Show all languages with coverage
    for lang in $LANGUAGES; do
        po_file="translations/${lang}/LC_MESSAGES/messages.po"
        if [ -f "$po_file" ]; then
            # Count translated strings (non-empty msgstr)
            translated=$(grep -A1 '^msgstr' "$po_file" | grep -v '^--$' | grep -v '^msgstr ""$' | grep '^msgstr' | wc -l | tr -d ' ')

            # Count fuzzy strings
            fuzzy=$(grep -c '^#, fuzzy' "$po_file" 2>/dev/null || echo "0")

            if [ "$total_strings" -gt 0 ]; then
                percentage=$(( (translated * 100) / total_strings ))

                # Format output with colors based on percentage
                if [ "$percentage" -ge 80 ]; then
                    status="✅"
                elif [ "$percentage" -ge 50 ]; then
                    status="⚠️ "
                else
                    status="❌"
                fi

                printf "  %s %-5s: %4d/%4d (%3d%%) " "$status" "$lang" "$translated" "$total_strings" "$percentage"

                if [ "$fuzzy" -gt 0 ]; then
                    printf "[%d fuzzy]" "$fuzzy"
                fi

                echo
            fi
        else
            printf "  ⚪ %-5s: not initialized\n" "$lang"
        fi
    done

    echo
    echo "Legend:"
    echo "  ✅ = 80%+ translated (ready for use)"
    echo "  ⚠️  = 50-79% translated (partial support)"
    echo "  ❌ = <50% translated (needs work)"
    echo "  ⚪ = not initialized"
}

run_full_workflow() {
    echo "🚀 Running full translation workflow..."
    echo "======================================"

    extract_translations
    echo
    update_translations
    echo
    compile_translations
    echo

    echo "🎉 Full workflow complete!"
    echo
    echo "Next steps:"
    echo "1. Upload to Crowdin: $0 upload"
    echo "2. Translators work on crowdin.com"
    echo "3. Download translations: $0 download"
}

# Parse command line arguments
COMMAND=""
TARGET_LANG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        extract|init|update|compile|upload|download|glossary|status|full)
            COMMAND="$1"
            shift
            ;;
        -l|--lang)
            TARGET_LANG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    extract)
        extract_translations
        ;;
    init)
        init_translations "$TARGET_LANG"
        ;;
    update)
        update_translations "$TARGET_LANG"
        ;;
    compile)
        compile_translations "$TARGET_LANG"
        ;;
    upload)
        upload_to_crowdin
        ;;
    download)
        download_from_crowdin
        ;;
    glossary)
        upload_glossary
        ;;
    status)
        show_status
        ;;
    full)
        run_full_workflow
        ;;
    "")
        echo "Error: No command specified"
        show_help
        exit 1
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_help
        exit 1
        ;;
esac