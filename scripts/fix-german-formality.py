#!/usr/bin/env python3
import re
import sys

def fix_formality(text):
    """Convert formal German (Sie) to informal (du)."""
    
    # Create a mapping of formal to informal forms
    replacements = [
        # Direct Sie/Ihnen forms (case-sensitive)
        (r'\bSie\s+sind\b', 'du bist'),
        (r'\bSie\s+haben\b', 'du hast'),
        (r'\bSie\s+können\b', 'du kannst'),
        (r'\bSie\s+müssen\b', 'du musst'),
        (r'\bSie\s+möchten\b', 'du möchtest'),
        (r'\bSie\s+wollen\b', 'du willst'),
        (r'\bSie\s+sollen\b', 'du sollst'),
        (r'\bSie\s+werden\b', 'du wirst'),
        (r'\bSie\s+dürfen\b', 'du darfst'),
        
        # Imperative forms
        (r'\bBitte\s+konfigurieren\s+Sie\b', 'Bitte konfiguriere'),
        (r'\bBitte\s+fügen\s+Sie\b', 'Bitte füge'),
        (r'\bBitte\s+verwenden\s+Sie\b', 'Bitte verwende'),
        (r'\bBitte\s+legen\s+Sie\b', 'Bitte lege'),
        (r'\bBitte\s+wenden\s+Sie\s+sich\b', 'Bitte wende dich'),
        (r'\bBitte\s+halten\s+Sie\b', 'Bitte halte'),
        (r'\bBitte\s+aktivieren\s+Sie\b', 'Bitte aktiviere'),
        (r'\bBitte\s+erwägen\s+Sie\b', 'Bitte erwäge'),
        
        # Other imperative patterns
        (r'\bVerwenden\s+Sie\b', 'Verwende'),
        (r'\bWählen\s+Sie\b', 'Wähle'),
        (r'\bGeben\s+Sie\b', 'Gib'),
        (r'\bPrüfen\s+Sie\b', 'Prüfe'),
        (r'\bDefinieren\s+Sie\b', 'Definiere'),
        (r'\bKlicken\s+Sie\b', 'Klicke'),
        (r'\bBesuchen\s+Sie\b', 'Besuche'),
        (r'\bErfüllen\s+Sie\b', 'Erfülle'),
        (r'\bAktivieren\s+Sie\b', 'Aktiviere'),
        (r'\bBeginnen\s+Sie\b', 'Beginne'),
        (r'\bÜberlegen\s+Sie\b', 'Überlege'),
        (r'\bSichern\s+Sie\b', 'Sichere'),
        (r'\bErstellen\s+Sie\b', 'Erstelle'),
        (r'\bTippen\s+Sie\b', 'Tippe'),
        (r'\bScannen\s+Sie\b', 'Scanne'),
        (r'\bBenutzen\s+Sie\b', 'Benutze'),
        (r'\bÜberprüfen\s+Sie\b', 'Überprüfe'),
        (r'\bLöschen\s+Sie\b', 'Lösche'),
        (r'\bFügen\s+Sie\b', 'Füge'),
        
        # Questions with Sie
        (r'\bSind\s+Sie\s+sicher\b', 'Bist du sicher'),
        (r'\bMöchten\s+Sie\b', 'Möchtest du'),
        (r'\bWie\s+möchten\s+Sie\b', 'Wie möchtest du'),
        
        # Possessive pronouns
        (r'\bIhre\s+', 'deine '),
        (r'\bIhren\s+', 'deinen '),
        (r'\bIhrer\s+', 'deiner '),
        (r'\bIhrem\s+', 'deinem '),
        (r'\bIhres\s+', 'deines '),
        (r'\bIhr\s+Inventar\b', 'dein Inventar'),
        (r'\bIhr\s+Arzt', 'dein Arzt'),
        (r'\bIhrem\s+Inventar\b', 'deinem Inventar'),
        (r'\bIhrem\s+Besuch\b', 'deinem Besuch'),
        (r'\bIhrem\s+Arztbesuch\b', 'deinem Arztbesuch'),
        (r'\bIhren\s+vorgegebenen\b', 'deinen vorgegebenen'),
        (r'\bIhres\s+bevorstehenden\b', 'deines bevorstehenden'),
        
        # Fix some common context patterns
        (r'für\s+Ihren\s+', 'für deinen '),
        (r'aus\s+Ihrem\s+', 'aus deinem '),
        (r'nach\s+Ihren\s+', 'nach deinen '),
        (r'mit\s+Ihrem\s+', 'mit deinem '),
        (r'vor\s+Ihrem\s+', 'vor deinem '),
        
        # Standalone possessives
        (r'\bIhre\b', 'deine'),
        (r'\bIhrer\b', 'deiner'),
        (r'\bIhrem\b', 'deinem'),
        (r'\bIhren\b', 'deinen'),
        (r'\bIhres\b', 'deines'),
        (r'\bIhr\b(?!\w)', 'dein'),
        
        # Some specific context fixes
        (r'um\s+Ihr\s+', 'um dein '),
        (r'automatisch\s+mit\s+Ihr\s+', 'automatisch mit dein '),
        
        # Fix any remaining "Sie" at word boundaries
        (r'(?<=\s)Sie\b(?!\s+sich)', 'du'),
        (r'^Sie\b(?!\s+sich)', 'Du'),
        
        # Fix reflexive forms that got messed up
        (r'\bwende\s+du\s+dich\b', 'wende dich'),
        (r'\bsich\s+an\b', 'dich an'),
    ]
    
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    
    # Fix capitalization at sentence start
    result = re.sub(r'^du\b', 'Du', result)
    result = re.sub(r'(\. )du\b', r'\1Du', result)
    result = re.sub(r'(! )du\b', r'\1Du', result)
    result = re.sub(r'(\? )du\b', r'\1Du', result)
    
    return result

def process_po_file(filepath):
    """Process a .po file and convert formal to informal German."""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_msgstr = False
    modified_lines = []
    
    for line in lines:
        if line.startswith('msgstr "'):
            # Single-line msgstr
            if line.strip().endswith('"'):
                # Extract content between quotes
                match = re.match(r'msgstr "(.*)"', line.strip())
                if match:
                    content = match.group(1)
                    fixed_content = fix_formality(content)
                    if content != fixed_content:
                        print(f"Fixed: {content[:50]}... -> {fixed_content[:50]}...")
                    line = f'msgstr "{fixed_content}"\n'
            in_msgstr = True
        elif in_msgstr and line.startswith('"') and line.strip().endswith('"'):
            # Multi-line msgstr continuation
            match = re.match(r'"(.*)"', line.strip())
            if match:
                content = match.group(1)
                fixed_content = fix_formality(content)
                if content != fixed_content:
                    print(f"Fixed: {content[:50]}... -> {fixed_content[:50]}...")
                line = f'"{fixed_content}"\n'
        elif not line.startswith('"'):
            in_msgstr = False
        
        modified_lines.append(line)
    
    # Write back the modified content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)
    
    print(f"Processed {filepath}")

if __name__ == "__main__":
    # Process the German translation file
    po_file = "translations/de/LC_MESSAGES/messages.po"
    process_po_file(po_file)
    print("Conversion from formal (Sie) to informal (du) completed.")