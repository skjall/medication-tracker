#!/bin/bash

# Translation Coverage Report Script
# This script calculates translation completion percentages for all languages

echo "Translation Coverage Report"
echo "=========================="
echo "Total strings: $(grep -c '^msgid ' translations/messages.pot) strings"
echo

# Check if translations directory exists
if [ ! -d "translations" ]; then
    echo "Error: translations directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Initialize variables for summary
total_languages=0
complete_languages=0
threshold=80

echo "Language Coverage Report:"
echo "------------------------"

# Process each language directory
for lang_dir in translations/*/LC_MESSAGES; do
    if [ -d "$lang_dir" ]; then
        lang=$(basename $(dirname $lang_dir))
        
        # Skip English (always 100%)
        if [[ $lang == "en" ]]; then
            echo "en (English):     714/714 (100.0%) ✅"
            total_languages=$((total_languages + 1))
            complete_languages=$((complete_languages + 1))
            continue
        fi
        
        po_file="$lang_dir/messages.po"
        
        if [ -f "$po_file" ]; then
            total_languages=$((total_languages + 1))
            
            # Get translation statistics using msgfmt
            stats=$(msgfmt --statistics "$po_file" 2>&1)
            
            # Extract translated count
            translated=$(echo "$stats" | grep -o '[0-9]\+ translated' | cut -d' ' -f1)
            if [ -z "$translated" ]; then
                translated=0
            fi
            
            # Calculate total strings and percentage
            total=714  # Total strings from .pot file
            if [ $total -gt 0 ]; then
                percentage=$(echo "scale=1; $translated * 100 / $total" | bc -l)
            else
                percentage=0
            fi
            
            # Check if above threshold
            threshold_check=""
            if (( $(echo "$percentage >= $threshold" | bc -l) )); then
                threshold_check="✅"
                complete_languages=$((complete_languages + 1))
            else
                threshold_check="❌"
            fi
            
            # Get language name
            case $lang in
                de) lang_name="German" ;;
                es) lang_name="Spanish" ;;
                fr) lang_name="French" ;;
                *) lang_name="Unknown" ;;
            esac
            
            printf "%-2s (%-8s): %3s/%3s (%5.1f%%) %s\n" "$lang" "$lang_name" "$translated" "$total" "$percentage" "$threshold_check"
        else
            echo "$lang: No .po file found ❌"
            total_languages=$((total_languages + 1))
        fi
    fi
done

echo
echo "Summary:"
echo "--------"
echo "Total languages configured: $total_languages"
echo "Languages meeting ${threshold}% threshold: $complete_languages"
echo "Languages visible in UI: $complete_languages (+ English)"

# Show which languages are hidden
hidden_count=$((total_languages - complete_languages))
if [ $hidden_count -gt 0 ]; then
    echo "Languages hidden due to low coverage: $hidden_count"
fi

echo
echo "Legend:"
echo "✅ = Available in language selector (≥${threshold}% complete)"
echo "❌ = Hidden from language selector (<${threshold}% complete)"

echo
echo "To update translations:"
echo "1. Extract strings:    cd app && pybabel extract -F ../babel.cfg -k _ -o ../translations/messages.pot ."
echo "2. Update languages:   pybabel update -i translations/messages.pot -d translations"
echo "3. Upload to Crowdin:  crowdin upload sources"
echo "4. Download from Crowdin: crowdin download"
echo "5. Compile translations: pybabel compile -d translations"