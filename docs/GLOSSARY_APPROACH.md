# Glossary Management Approach

## Overview
This document describes the approach for managing the multilingual glossary for the Medication Tracker application.

## Glossary Structure

### Format Choice: CSV
We use CSV format for the glossary because:
- Simple to edit and maintain
- Well-supported by Crowdin
- Easy to version control
- Can handle multiple languages per concept

### Structure
Each row represents a **concept** with terms in multiple languages:
- **Concept-level fields**: Definition, subject area, notes
- **Language-specific fields**: Terms, descriptions, parts of speech, gender, status

### Key Principles

1. **One Concept Per Row**
   - Each row represents a single concept that may have different terms in different languages
   - Example: "Medication" (EN) = "Medikament" (DE)

2. **Informal Language (Du-Form)**
   - German translations use informal "du" instead of formal "Sie"
   - More appropriate for personal health management software
   - Creates a friendlier user experience

3. **Terminology Corrections**
   - "Prescription Template" → "Order Template" (Bestellformular)
   - The feature generates order forms for physicians, not prescriptions
   - Prescriptions (Rezepte) are separate medical documents

4. **Non-Translatable Terms**
   - German package sizes (N1, N2, N3) remain unchanged
   - These are standardized codes in the German pharmacy system

## Language-Specific Guidelines

### German (DE)
- Use medical terminology familiar to German patients
- Include grammatical gender for nouns
- Provide both formal medical terms and common alternatives where appropriate
- Example: "Physician" = "Arzt/Ärztin" (gendered) or "Arzt" (generic)

### English (EN)
- Use clear, non-technical language where possible
- Provide context for specialized terms
- Include both US and UK spellings where they differ

## Fields Description

### Concept Fields
- `Concept Definition`: Technical definition of the concept
- `Concept Subject`: Domain area (Healthcare, Pharmacy, System Feature, etc.)
- `Concept Note`: Additional context or usage notes
- `Translatable`: Whether the term should be translated (no for codes like N1/N2/N3)

### Language-Specific Fields
- `Term [lang]`: The actual term in that language
- `Description [lang]`: User-friendly description
- `Part of Speech [lang]`: Grammatical category (noun, verb, adjective)
- `Status [lang]`: Preferred, deprecated, or alternative
- `Type [lang]`: Full form, abbreviation, etc.
- `Gender [lang]`: Grammatical gender (for languages that have it)
- `Note [lang]`: Language-specific usage notes

## Maintenance Process

1. **Review Translations**: Regularly review actual translations for consistency
2. **Identify Gaps**: Find terms used in the app but missing from glossary
3. **Add Context**: Provide sufficient context for accurate translation
4. **Test with Native Speakers**: Validate terminology with native speakers
5. **Update Regularly**: Keep glossary synchronized with application changes

## Common Issues and Solutions

### Issue: Formal vs Informal Language
**Solution**: Consistently use informal "du" form in German for personal health software

### Issue: Medical Jargon
**Solution**: Provide both technical and lay terms where appropriate

### Issue: Gender-Specific Terms
**Solution**: Use inclusive language or provide both forms (Arzt/Ärztin)

### Issue: Regional Variations
**Solution**: Note regional differences in the notes field

## Upload to Crowdin

```bash
# Upload the glossary to existing glossary ID
./scripts/upload-glossary.sh

# The script uses the glossary ID: 612724
# Format: CSV with headers
# Encoding: UTF-8
```

## File Locations

- **Glossary File**: `/crowdin-glossary.csv`
- **Upload Script**: `/scripts/upload-glossary.sh`
- **Documentation**: `/docs/GLOSSARY_APPROACH.md`