#!/usr/bin/env python3
"""
Clean glossary upload - uploads concepts without duplicates and with full metadata
"""

import csv
import requests
import os
import time
import sys
from collections import OrderedDict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv('CROWDIN_API_TOKEN')
GLOSSARY_ID = 612724
BASE_URL = 'https://api.crowdin.com/api/v2'

if not API_TOKEN:
    print("❌ CROWDIN_API_TOKEN not found in .env file")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}


def clear_glossary():
    """Clear all existing terms from glossary"""
    print("🗑️  Clearing existing glossary...")
    
    # Get all terms
    all_terms = []
    offset = 0
    limit = 500
    
    while True:
        response = requests.get(
            f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms',
            headers=headers,
            params={'limit': limit, 'offset': offset}
        )
        
        if response.status_code != 200:
            break
            
        data = response.json()
        terms = data.get('data', [])
        all_terms.extend([t['data']['id'] for t in terms])
        
        # Check pagination
        total = data.get('pagination', {}).get('total', 0)
        if offset + limit >= total:
            break
        offset += limit
    
    # Delete all terms
    for i, term_id in enumerate(all_terms, 1):
        requests.delete(
            f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms/{term_id}',
            headers=headers
        )
        if i % 50 == 0:
            print(f"   Deleted {i}/{len(all_terms)} terms...")
            time.sleep(0.5)
    
    print(f"   ✅ Deleted {len(all_terms)} terms")
    return len(all_terms)


def parse_glossary_csv(filepath):
    """Parse CSV and remove duplicates"""
    print("📖 Reading and cleaning glossary...")
    
    concepts = OrderedDict()  # Preserve order, remove duplicates
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            en_term = row.get('Term [en]', '').strip()
            if not en_term:
                continue
            
            # Skip if already seen (duplicate)
            if en_term in concepts:
                continue
            
            # Store concept data
            concepts[en_term] = {
                'en': {
                    'text': en_term,
                    'description': row.get('Description [en]', '').strip(),
                    'partOfSpeech': row.get('Part of Speech [en]', '').strip().lower(),
                    'status': row.get('Status [en]', 'preferred').strip().lower(),
                    'note': row.get('Note [en]', '').strip()
                },
                'de': {
                    'text': row.get('Term [de]', '').strip(),
                    'description': row.get('Description [de]', '').strip(),
                    'partOfSpeech': row.get('Part of Speech [de]', '').strip().lower(),
                    'status': row.get('Status [de]', 'preferred').strip().lower(),
                    'gender': row.get('Gender [de]', '').strip().lower(),
                    'note': row.get('Note [de]', '').strip()
                } if row.get('Term [de]') else None
            }
    
    print(f"   Found {len(concepts)} unique concepts")
    return concepts


def upload_concept(en_term, concept_data):
    """Upload a single concept with English and German terms"""
    
    # Prepare English term payload
    en_data = concept_data['en']
    en_payload = {
        'languageId': 'en',
        'text': en_data['text']
    }
    
    # Add optional fields
    if en_data['description']:
        en_payload['description'] = en_data['description']
    
    if en_data['partOfSpeech'] in ['noun', 'verb', 'adjective', 'adverb', 'pronoun', 
                                    'interjection', 'numeral', 'determiner', 'particle']:
        en_payload['partOfSpeech'] = en_data['partOfSpeech']
    elif en_data['partOfSpeech'] == 'proper noun':
        en_payload['partOfSpeech'] = 'proper noun'
        
    if en_data['status'] in ['preferred', 'admitted', 'not recommended', 'obsolete']:
        en_payload['status'] = en_data['status']
        
    if en_data['note']:
        en_payload['note'] = en_data['note']
    
    # Create English term (creates concept)
    response = requests.post(
        f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms',
        headers=headers,
        json=en_payload
    )
    
    if response.status_code != 201:
        return False
    
    concept_id = response.json()['data']['conceptId']
    
    # Add German translation if present
    de_data = concept_data.get('de')
    if de_data and de_data['text']:
        de_payload = {
            'languageId': 'de',
            'text': de_data['text'],
            'conceptId': concept_id  # Link to same concept
        }
        
        # Add optional German fields
        if de_data['description']:
            de_payload['description'] = de_data['description']
            
        if de_data['partOfSpeech'] in ['noun', 'verb', 'adjective', 'adverb', 'pronoun',
                                        'interjection', 'numeral', 'determiner', 'particle']:
            de_payload['partOfSpeech'] = de_data['partOfSpeech']
            
        if de_data['gender'] in ['masculine', 'feminine', 'neuter']:
            de_payload['gender'] = de_data['gender']
            
        if de_data['status'] in ['preferred', 'admitted', 'not recommended', 'obsolete']:
            de_payload['status'] = de_data['status']
            
        if de_data['note']:
            de_payload['note'] = de_data['note']
        
        # Create German term
        response = requests.post(
            f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms',
            headers=headers,
            json=de_payload
        )
    
    return True


def main():
    print("🔧 Clean Glossary Upload to Crowdin")
    print("=" * 40)
    
    # Step 1: Clear existing glossary
    deleted_count = clear_glossary()
    
    # Step 2: Parse and clean CSV
    concepts = parse_glossary_csv('crowdin-glossary.csv')
    
    # Step 3: Upload concepts
    print("\n📤 Uploading concepts with full metadata...")
    
    uploaded = 0
    failed = []
    
    for i, (en_term, concept_data) in enumerate(concepts.items(), 1):
        if upload_concept(en_term, concept_data):
            uploaded += 1
            de_term = concept_data.get('de', {}).get('text', 'N/A') if concept_data.get('de') else 'N/A'
            print(f"   ✅ {uploaded}. {en_term} / {de_term}")
        else:
            failed.append(en_term)
            print(f"   ❌ Failed: {en_term}")
        
        # Progress and rate limiting
        if i % 20 == 0:
            print(f"      Progress: {i}/{len(concepts)} concepts...")
            time.sleep(1)
        
        # Limit for initial test
        if uploaded >= 100:
            print("\n   (Limiting to 100 concepts for this run)")
            break
    
    # Step 4: Verify
    print("\n📊 Final Statistics:")
    print(f"   • Uploaded: {uploaded} concepts")
    print(f"   • Failed: {len(failed)} concepts")
    
    # Check actual counts
    response = requests.get(
        f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms?limit=1',
        headers=headers
    )
    
    if response.status_code == 200:
        total_terms = response.json()['pagination']['total']
        print(f"   • Total terms in glossary: {total_terms}")
        print(f"   • Average terms per concept: {total_terms/uploaded:.1f}" if uploaded > 0 else "")
    
    print("\n✨ Done!")
    
    if failed:
        print("\nFailed concepts:")
        for term in failed[:10]:
            print(f"   - {term}")
        if len(failed) > 10:
            print(f"   ... and {len(failed)-10} more")


if __name__ == '__main__':
    main()