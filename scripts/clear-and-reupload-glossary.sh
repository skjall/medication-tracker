#!/bin/bash

set -e

# Load environment variables
source .env

echo "🗑️  Clearing Crowdin Glossary"
echo "============================="

# Get all concept IDs from the glossary
echo "📊 Fetching all concepts from glossary ID 612724..."
CONCEPTS=$(curl -s -X GET "https://api.crowdin.com/api/v2/glossaries/612724/concepts?limit=500" \
  -H "Authorization: Bearer $CROWDIN_API_TOKEN" \
  -H "Content-Type: application/json" | python -c "
import json, sys
data = json.load(sys.stdin)
if 'data' in data:
    for item in data['data']:
        if 'data' in item and 'id' in item['data']:
            print(item['data']['id'])
")

# Count concepts
CONCEPT_COUNT=$(echo "$CONCEPTS" | wc -l | tr -d ' ')
echo "Found $CONCEPT_COUNT concepts to delete"

# Delete each concept
if [ -n "$CONCEPTS" ]; then
    echo "🗑️  Deleting all concepts..."
    for CONCEPT_ID in $CONCEPTS; do
        echo -n "  Deleting concept $CONCEPT_ID... "
        curl -s -X DELETE "https://api.crowdin.com/api/v2/glossaries/612724/concepts/$CONCEPT_ID" \
          -H "Authorization: Bearer $CROWDIN_API_TOKEN" \
          -H "Content-Type: application/json" > /dev/null
        echo "✓"
    done
    echo "✅ All concepts deleted"
else
    echo "ℹ️  No concepts to delete"
fi

echo ""
echo "📤 Re-uploading clean glossary..."
echo "================================="

# Now upload the new glossary
crowdin glossary upload crowdin-glossary.csv \
    --id=612724 \
    --scheme="term_en=0" \
    --scheme="description_en=1" \
    --scheme="part_of_speech_en=2" \
    --scheme="status_en=3" \
    --scheme="type_en=4" \
    --scheme="gender_en=5" \
    --scheme="note_en=6" \
    --scheme="term_de=7" \
    --scheme="description_de=8" \
    --scheme="part_of_speech_de=9" \
    --scheme="status_de=10" \
    --scheme="type_de=11" \
    --scheme="gender_de=12" \
    --scheme="note_de=13" \
    --scheme="concept_definition=14" \
    --scheme="concept_subject=15" \
    --scheme="concept_note=16" \
    --first-line-contains-header

echo ""
echo "✅ Glossary cleared and re-uploaded successfully!"
echo ""
echo "📊 Verifying new glossary..."
NEW_COUNT=$(curl -s -X GET "https://api.crowdin.com/api/v2/glossaries/612724/concepts?limit=1" \
  -H "Authorization: Bearer $CROWDIN_API_TOKEN" \
  -H "Content-Type: application/json" | python -c "
import json, sys
data = json.load(sys.stdin)
if 'pagination' in data and 'total' in data['pagination']:
    print(data['pagination']['total'])
else:
    print('0')
")

echo "New glossary has $NEW_COUNT concepts"