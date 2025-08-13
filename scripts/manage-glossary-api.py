#!/usr/bin/env python3
"""
Manage Crowdin glossary via API - clear old entries and upload new ones.
Using the Terms API instead of Concepts API.
"""

import csv
import json
import os
import sys
import time
from typing import Dict, List, Any, Optional
import requests
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv('CROWDIN_API_TOKEN')
PROJECT_ID = os.getenv('CROWDIN_PROJECT_ID', '819294')
GLOSSARY_ID = 612724
BASE_URL = 'https://api.crowdin.com/api/v2'

if not API_TOKEN:
    print("❌ CROWDIN_API_TOKEN not found in .env file")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}


def get_all_terms() -> List[int]:
    """Fetch all term IDs from the glossary."""
    print("📊 Fetching existing terms...")
    
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
            print(f"❌ Failed to fetch terms: {response.text}")
            return []
        
        data = response.json()
        terms = data.get('data', [])
        
        for term in terms:
            term_id = term['data']['id']
            all_terms.append(term_id)
        
        # Check if there are more pages
        pagination = data.get('pagination', {})
        total = pagination.get('total', 0)
        
        if offset + limit >= total:
            break
        
        offset += limit
    
    print(f"   Found {len(all_terms)} existing terms")
    return all_terms


def delete_all_terms(term_ids: List[int]) -> bool:
    """Delete all terms from the glossary."""
    if not term_ids:
        print("ℹ️  No terms to delete")
        return True
    
    print(f"🗑️  Deleting {len(term_ids)} terms...")
    
    deleted = 0
    for i, term_id in enumerate(term_ids, 1):
        response = requests.delete(
            f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms/{term_id}',
            headers=headers
        )
        
        if response.status_code in [204, 404]:  # 204 = success, 404 = already deleted
            deleted += 1
        else:
            print(f"   ⚠️  Failed to delete term {term_id}: {response.status_code}")
        
        # Progress indicator
        if i % 50 == 0:
            print(f"   Deleted {deleted}/{i} terms...")
            time.sleep(0.5)  # Small delay to avoid rate limiting
    
    print(f"✅ Deleted {deleted}/{len(term_ids)} terms successfully")
    return True


def parse_glossary_csv(filepath: str) -> List[Dict[str, Any]]:
    """Parse the glossary CSV file into terms."""
    print(f"📖 Reading glossary from {filepath}...")
    
    terms = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Skip empty rows or rows without English term
            if not row.get('Term [en]'):
                continue
            
            # Create English term
            en_term = {
                'languageId': 'en',
                'text': row['Term [en]'],
                'isNewConcept': True  # Will create a new concept
            }
            
            # Add optional fields for English term
            if row.get('Description [en]'):
                en_term['description'] = row['Description [en]']
            if row.get('Part of Speech [en]'):
                pos = row['Part of Speech [en]'].lower()
                # Map to valid Crowdin values
                if pos in ['noun', 'verb', 'adjective', 'adverb', 'pronoun', 'interjection', 'numeral', 'determiner', 'particle']:
                    en_term['partOfSpeech'] = pos
                elif pos == 'proper noun':
                    en_term['partOfSpeech'] = 'proper noun'
                else:
                    en_term['partOfSpeech'] = 'other'
            if row.get('Status [en]'):
                en_term['status'] = row['Status [en]'].lower()
            if row.get('Note [en]'):
                en_term['note'] = row['Note [en]']
            
            terms.append(en_term)
            
            # Add German term if present (will be linked to same concept)
            if row.get('Term [de]'):
                de_term = {
                    'languageId': 'de',
                    'text': row['Term [de]'],
                    'relatedEnglishTerm': row['Term [en]']  # Custom field to track relationship
                }
                
                # Add optional fields for German term
                if row.get('Description [de]'):
                    de_term['description'] = row['Description [de]']
                if row.get('Part of Speech [de]'):
                    pos = row['Part of Speech [de]'].lower()
                    if pos in ['noun', 'verb', 'adjective', 'adverb', 'pronoun', 'interjection', 'numeral', 'determiner', 'particle']:
                        de_term['partOfSpeech'] = pos
                    elif pos == 'proper noun':
                        de_term['partOfSpeech'] = 'proper noun'
                    else:
                        de_term['partOfSpeech'] = 'other'
                if row.get('Status [de]'):
                    de_term['status'] = row['Status [de]'].lower()
                if row.get('Gender [de]'):
                    gender = row['Gender [de]'].lower()
                    if gender in ['masculine', 'feminine', 'neuter', 'other']:
                        de_term['gender'] = gender
                if row.get('Note [de]'):
                    de_term['note'] = row['Note [de]']
                
                terms.append(de_term)
    
    print(f"   Parsed {len(terms)} terms from CSV")
    return terms


def create_term(term: Dict[str, Any], concept_map: Dict[str, int]) -> Optional[int]:
    """
    Create a single term in the glossary.
    Returns the concept ID if successful, None otherwise.
    """
    
    # Prepare the request payload
    payload = {
        'languageId': term['languageId'],
        'text': term['text']
    }
    
    # Add optional fields
    optional_fields = ['description', 'partOfSpeech', 'status', 'type', 'gender', 'note']
    for field in optional_fields:
        if field in term and term[field]:
            payload[field] = term[field]
    
    # For German terms, link to the English concept if it exists
    if 'relatedEnglishTerm' in term:
        english_term = term['relatedEnglishTerm']
        if english_term in concept_map:
            payload['conceptId'] = concept_map[english_term]
    
    response = requests.post(
        f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms',
        headers=headers,
        json=payload
    )
    
    if response.status_code == 201:
        data = response.json()
        concept_id = data['data']['conceptId']
        
        # Store concept ID for English terms
        if term['languageId'] == 'en' and 'relatedEnglishTerm' not in term:
            concept_map[term['text']] = concept_id
        
        return concept_id
    else:
        print(f"   ❌ Failed to create term '{term['text']}' ({term['languageId']}): {response.status_code}")
        if response.text and len(response.text) < 200:
            print(f"      Response: {response.text}")
        return None


def upload_terms(terms: List[Dict[str, Any]]) -> bool:
    """Upload all terms to the glossary."""
    
    # Separate English and German terms
    english_terms = [t for t in terms if t['languageId'] == 'en']
    german_terms = [t for t in terms if t['languageId'] == 'de']
    
    print(f"📤 Uploading {len(english_terms)} English terms and {len(german_terms)} German terms...")
    
    concept_map = {}  # Maps English term text to concept ID
    success_count = 0
    
    # First upload English terms to create concepts
    print(f"\n   Creating concepts with English terms...")
    for i, term in enumerate(english_terms, 1):
        concept_id = create_term(term, concept_map)
        if concept_id is not None:
            success_count += 1
        
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(english_terms)} English terms...")
        
        # Small delay to avoid rate limiting
        if i % 50 == 0:
            time.sleep(1)
    
    print(f"   ✅ Created {len(concept_map)} concepts")
    
    # Then upload German terms linked to the same concepts
    if german_terms:
        print(f"\n   Adding German translations...")
        german_success = 0
        for i, term in enumerate(german_terms, 1):
            concept_id = create_term(term, concept_map)
            if concept_id is not None:
                success_count += 1
                german_success += 1
            
            if i % 20 == 0:
                print(f"   Progress: {i}/{len(german_terms)} German terms...")
            
            # Small delay to avoid rate limiting
            if i % 50 == 0:
                time.sleep(1)
        
        print(f"   ✅ Added {german_success} German translations")
    
    print(f"\n✅ Successfully uploaded {success_count}/{len(terms)} terms total")
    return success_count > 0


def verify_glossary() -> tuple[int, int]:
    """Verify the number of terms and concepts in the glossary."""
    # Get term count
    response = requests.get(
        f'{BASE_URL}/glossaries/{GLOSSARY_ID}/terms',
        headers=headers,
        params={'limit': 1}
    )
    
    term_count = 0
    if response.status_code == 200:
        data = response.json()
        term_count = data.get('pagination', {}).get('total', 0)
    
    # Get concept count
    response = requests.get(
        f'{BASE_URL}/glossaries/{GLOSSARY_ID}/concepts',
        headers=headers,
        params={'limit': 1}
    )
    
    concept_count = 0
    if response.status_code == 200:
        data = response.json()
        concept_count = data.get('pagination', {}).get('total', 0)
    
    return term_count, concept_count


def main():
    """Main function to manage the glossary."""
    print("🔧 Crowdin Glossary Management via API (Terms-based)")
    print("=" * 53)
    
    # Step 1: Delete all existing terms
    print("\n📋 Step 1: Clear existing glossary")
    existing_terms = get_all_terms()
    if existing_terms:
        delete_all_terms(existing_terms)
    
    # Verify deletion
    term_count, concept_count = verify_glossary()
    if term_count > 0:
        print(f"   ⚠️  {term_count} terms still remain in glossary")
    else:
        print("   ✅ Glossary cleared successfully")
    
    # Step 2: Parse the CSV file
    print("\n📋 Step 2: Parse glossary CSV")
    csv_path = Path(__file__).parent.parent / 'crowdin-glossary.csv'
    terms = parse_glossary_csv(str(csv_path))
    
    if not terms:
        print("❌ No terms found in CSV file")
        sys.exit(1)
    
    english_count = len([t for t in terms if t['languageId'] == 'en'])
    german_count = len([t for t in terms if t['languageId'] == 'de'])
    print(f"   Found {english_count} English terms and {german_count} German terms")
    
    # Step 3: Upload new terms
    print("\n📋 Step 3: Upload new terms")
    upload_terms(terms)
    
    # Step 4: Verify the upload
    print("\n📋 Step 4: Verify glossary")
    term_count, concept_count = verify_glossary()
    print(f"\n📊 Final glossary statistics:")
    print(f"   • {term_count} terms total")
    print(f"   • {concept_count} concepts")
    print(f"   • Average {term_count/concept_count:.1f} terms per concept" if concept_count > 0 else "")
    
    if concept_count == english_count:
        print(f"\n🎉 Glossary successfully updated with {concept_count} bilingual concepts!")
    else:
        print(f"\n⚠️  Expected {english_count} concepts but found {concept_count}")
        if concept_count > 0:
            print("   Some terms may have failed to upload or created duplicate concepts")
    
    print("\n✨ Done!")


if __name__ == '__main__':
    main()