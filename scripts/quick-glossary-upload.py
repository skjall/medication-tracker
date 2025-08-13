#!/usr/bin/env python3
"""
Quick glossary upload - uploads only the first 50 concepts as a test
"""

import csv
import json
import os
import sys
import requests

# Load API token from .env
API_TOKEN = None
with open('.env', 'r') as f:
    for line in f:
        if 'CROWDIN_API_TOKEN' in line:
            API_TOKEN = line.split('=')[1].strip().strip('"').strip("'")
            break

if not API_TOKEN:
    print("❌ CROWDIN_API_TOKEN not found in .env")
    sys.exit(1)

GLOSSARY_ID = 612724
BASE_URL = 'https://api.crowdin.com/api/v2'

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

print("📤 Quick glossary upload (first 50 concepts)")
print("=" * 40)

# Read and upload first 50 concepts
concepts_uploaded = 0
failed_concepts = []

with open('crowdin-glossary.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        if concepts_uploaded >= 50:
            break
            
        if not row.get('Term [en]'):
            continue
        
        # Create minimal payload
        payload = {
            'languageDetails': []
        }
        
        # Add concept metadata if available
        if row.get('Concept Definition'):
            payload['definition'] = row['Concept Definition']
        if row.get('Concept Subject'):
            payload['subject'] = row['Concept Subject']
        
        # Add English term (required)
        en_term = {
            'languageId': 'en',
            'terms': [{
                'text': row['Term [en]']
            }]
        }
        
        # Add optional English fields
        if row.get('Description [en]'):
            en_term['terms'][0]['description'] = row['Description [en]']
        if row.get('Part of Speech [en]'):
            en_term['terms'][0]['partOfSpeech'] = row['Part of Speech [en]']
            
        payload['languageDetails'].append(en_term)
        
        # Add German term if present
        if row.get('Term [de]'):
            de_term = {
                'languageId': 'de',
                'terms': [{
                    'text': row['Term [de]']
                }]
            }
            
            # Add optional German fields
            if row.get('Description [de]'):
                de_term['terms'][0]['description'] = row['Description [de]']
            if row.get('Part of Speech [de]'):
                de_term['terms'][0]['partOfSpeech'] = row['Part of Speech [de]']
            if row.get('Gender [de]'):
                de_term['terms'][0]['gender'] = row['Gender [de]']
                
            payload['languageDetails'].append(de_term)
        
        # Upload concept
        try:
            response = requests.post(
                f'{BASE_URL}/glossaries/{GLOSSARY_ID}/concepts',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                concepts_uploaded += 1
                print(f"✓ {concepts_uploaded}. {row['Term [en]']}")
            else:
                failed_concepts.append(row['Term [en]'])
                print(f"✗ {row['Term [en]']}: {response.status_code}")
                
        except Exception as e:
            failed_concepts.append(row['Term [en]'])
            print(f"✗ {row['Term [en]']}: {str(e)}")

print()
print(f"✅ Uploaded: {concepts_uploaded}/50 concepts")

if failed_concepts:
    print(f"❌ Failed: {len(failed_concepts)} concepts")
    for term in failed_concepts[:5]:
        print(f"   - {term}")
    if len(failed_concepts) > 5:
        print(f"   ... and {len(failed_concepts) - 5} more")

# Verify
response = requests.get(
    f'{BASE_URL}/glossaries/{GLOSSARY_ID}/concepts?limit=1',
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    total = data.get('pagination', {}).get('total', 0)
    print()
    print(f"📊 Glossary now has {total} concepts total")