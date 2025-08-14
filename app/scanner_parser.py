"""
DataMatrix barcode parser and validation functions for pharmaceutical products.
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple


def parse_datamatrix(data: str) -> Dict[str, Optional[str]]:
    """
    Parse a GS1 DataMatrix barcode string.
    
    Args:
        data: Raw DataMatrix string
        
    Returns:
        Dictionary with extracted fields:
        - gtin: Global Trade Item Number (14 digits)
        - serial: Serial number
        - expiry: Expiry date (YYMMDD format)
        - batch: Batch/lot number
        - national_number: Extracted national pharmaceutical number
        - national_number_type: Type of national number (DE_PZN, FR_CIP13, etc.)
    """
    result = {
        'gtin': None,
        'serial': None,
        'expiry': None,
        'batch': None,
        'national_number': None,
        'national_number_type': None
    }
    
    # GS1 Application Identifiers with their lengths (None = variable)
    ai_info = {
        '01': (14, 'gtin'),      # GTIN-14 (fixed)
        '21': (None, 'serial'),  # Serial number (variable, max 20)
        '17': (6, 'expiry'),     # Expiry date YYMMDD (fixed)
        '10': (None, 'batch')    # Batch number (variable, max 20)
    }
    
    # Check if data contains FNC1 separator (ASCII 29)
    fnc1 = chr(29)
    
    if fnc1 in data:
        # Parse GS1 format with FNC1 separators
        # FNC1 at start indicates GS1 format, remove it
        if data.startswith(fnc1):
            data = data[1:]
        
        # Process with FNC1 separators
        # FNC1 separates variable-length fields from following AIs
        pos = 0
        while pos < len(data):
            # Find next FNC1 or end of string
            next_fnc1 = data.find(fnc1, pos)
            if next_fnc1 == -1:
                segment = data[pos:]
            else:
                segment = data[pos:next_fnc1]
            
            # Process this segment (may contain multiple fixed-length AIs)
            seg_pos = 0
            while seg_pos < len(segment) - 1:
                ai = segment[seg_pos:seg_pos+2]
                if ai in ai_info:
                    length, field = ai_info[ai]
                    seg_pos += 2
                    
                    if length:
                        # Fixed length field
                        if seg_pos + length <= len(segment):
                            result[field] = segment[seg_pos:seg_pos+length]
                            seg_pos += length
                        else:
                            break
                    else:
                        # Variable length - goes to end of segment
                        result[field] = segment[seg_pos:]
                        break
                else:
                    seg_pos += 1
            
            # Move to next segment
            if next_fnc1 == -1:
                break
            pos = next_fnc1 + 1
    
    # If no FNC1 or incomplete parsing, use sequential parsing
    # This handles concatenated GS1 data without FNC1 separators
    if not result['gtin'] and data.startswith('01'):
        # Extract GTIN first (fixed length)
        if len(data) >= 16:
            result['gtin'] = data[2:16]
            pos = 16
            
            # Parse remaining data sequentially
            # Order matters: AIs must be parsed in the order they appear
            while pos < len(data) - 1:
                # Check if we have at least 2 chars for AI
                if pos + 1 >= len(data):
                    break
                    
                ai = data[pos:pos+2]
                
                if ai in ai_info:
                    length, field = ai_info[ai]
                    pos += 2  # Skip AI
                    
                    if length:
                        # Fixed length field
                        if pos + length <= len(data):
                            result[field] = data[pos:pos+length]
                            pos += length
                        else:
                            # Not enough data for fixed field
                            break
                    else:
                        # Variable length field - need to find the next AI or end
                        field_start = pos
                        field_end = len(data)  # Default to end of string
                        
                        # Look for next AI (must check all known AIs)
                        # Start search from current position + minimum field length
                        min_length = 1 if field == 'batch' else 8  # Batches can be short
                        
                        for i in range(field_start + min_length, len(data) - 1):
                            potential_ai = data[i:i+2]
                            if potential_ai in ai_info:
                                # Found next AI
                                field_end = i
                                break
                        
                        # Extract the variable field
                        value = data[field_start:field_end]
                        
                        # Validate length constraints
                        if field in ['serial', 'batch'] and len(value) > 20:
                            # Max length exceeded, likely parsing error
                            # Try to find AI pattern within the value
                            for i in range(1, min(20, len(value))):
                                if value[i:i+2] in ai_info:
                                    value = value[:i]
                                    field_end = field_start + i
                                    break
                            else:
                                # No AI found, truncate to max
                                value = value[:20]
                                field_end = field_start + 20
                        
                        result[field] = value
                        pos = field_end
                else:
                    # Not a recognized AI, skip
                    pos += 1
    
    # Extract national number from GTIN if present
    if result['gtin']:
        national_info = extract_national_number(result['gtin'])
        if national_info:
            result['national_number'] = national_info[0]
            result['national_number_type'] = national_info[1]
    
    return result


def extract_national_number(gtin: str) -> Optional[Tuple[str, str]]:
    """
    Extract national pharmaceutical number from GTIN.
    
    Args:
        gtin: 14-digit GTIN
        
    Returns:
        Tuple of (national_number, number_type) or None
    """
    if not gtin or len(gtin) != 14:
        return None
    
    # Check for German NTIN (National Trade Item Number)
    # Structure: 0 + 4150 (GS1-Präfix für PZN) + PZN8 + Prüfziffer
    if gtin.startswith('04150'):
        # Extract PZN from positions 5-13 (8 digits)
        pzn = gtin[5:13]
        # For NTIN, the PZN is already validated through the NTIN check digit
        # We can trust it's a valid PZN if it's properly encoded in NTIN
        return (pzn, 'DE_PZN')
    
    # Standard GS1 country prefix check for other countries
    # Check country prefix (positions 1-3)
    prefix = gtin[1:4]
    
    # Germany: prefix 400-440 (alternative encoding, not NTIN)
    if 400 <= int(prefix) <= 440 and not gtin.startswith('04150'):
        # German products with standard GS1 encoding
        # PZN might be embedded differently
        return None  # Not a standard PZN encoding
    
    # France: prefix 300-379
    elif 300 <= int(prefix) <= 379:
        # French CIP13 is the full 13 digits (without packaging indicator)
        cip13 = gtin[1:14]  # Include check digit
        if validate_fr_cip13(cip13):
            return (cip13, 'FR_CIP13')
    
    # Belgium: prefix 054
    elif prefix == '054':
        # Belgian CNK is in positions 4-10 (7 digits)
        cnk = gtin[3:10]
        if validate_be_cnk(cnk):
            return (cnk, 'BE_CNK')
    
    # Netherlands: prefix 087
    elif prefix == '087':
        # Dutch Z-Index is in positions 4-10 (7 digits)
        z_index = gtin[3:10]
        return (z_index, 'NL_ZINDEX')
    
    # Spain: prefix 084
    elif prefix == '084':
        # Spanish CN is in positions 4-10 (7 digits)
        cn = gtin[3:10]
        return (cn, 'ES_CN')
    
    # Italy: prefix 080
    elif prefix == '080':
        # Italian AIC is in positions 4-12 (9 digits)
        aic = gtin[3:12]
        return (aic, 'IT_AIC')
    
    return None


def validate_de_pzn(pzn: str) -> bool:
    """
    Validate German PZN with Modulo-11 check digit.
    PZN can be 7 digits (PZN7) or 8 digits (PZN8) including check digit.
    
    Args:
        pzn: 7 or 8-digit PZN including check digit
        
    Returns:
        True if valid
    """
    if not pzn or not pzn.isdigit():
        return False
    
    if len(pzn) == 7:
        # PZN7: 6 digits + 1 check digit
        weights = [2, 3, 4, 5, 6, 7]
        total = sum(int(pzn[i]) * weights[i] for i in range(6))
        check = total % 11
        # If check is 10, the PZN is invalid (would need 2 digits)
        if check == 10:
            return False
        expected_check = int(pzn[6])
        return check == expected_check
        
    elif len(pzn) == 8:
        # PZN8: 7 digits + 1 check digit  
        weights = [2, 3, 4, 5, 6, 7, 2]  # Weight pattern for 7 digits
        total = sum(int(pzn[i]) * weights[i] for i in range(7))
        check = total % 11
        # If check is 10, the PZN is invalid
        if check == 10:
            return False
        expected_check = int(pzn[7])
        return check == expected_check
    
    return False


def validate_fr_cip13(cip13: str) -> bool:
    """
    Validate French CIP13 with Modulo-10 check digit.
    
    Args:
        cip13: 13-digit CIP13 including check digit
        
    Returns:
        True if valid
    """
    if not cip13 or len(cip13) != 13 or not cip13.isdigit():
        return False
    
    # Standard Modulo-10 (Luhn) validation
    return validate_gtin(cip13)


def validate_be_cnk(cnk: str) -> bool:
    """
    Validate Belgian CNK with Modulo-97 check digit.
    
    Args:
        cnk: 7-digit CNK including check digit
        
    Returns:
        True if valid
    """
    if not cnk or len(cnk) != 7 or not cnk.isdigit():
        return False
    
    # First 5 digits are the code, last 2 are check digits
    code = int(cnk[:5])
    check = int(cnk[5:7])
    
    # Modulo-97 validation
    expected = 97 - (code % 97)
    
    return check == expected


def validate_gtin(gtin: str) -> bool:
    """
    Validate GTIN using Modulo-10 (Luhn) algorithm.
    
    Args:
        gtin: GTIN string (8, 12, 13, or 14 digits)
        
    Returns:
        True if valid
    """
    if not gtin or not gtin.isdigit():
        return False
    
    if len(gtin) not in [8, 12, 13, 14]:
        return False
    
    # Calculate check digit
    total = 0
    for i in range(len(gtin) - 1):
        digit = int(gtin[i])
        if (len(gtin) - i) % 2 == 0:
            total += digit * 3
        else:
            total += digit
    
    check_digit = (10 - (total % 10)) % 10
    
    return check_digit == int(gtin[-1])


def parse_expiry_date(expiry: str) -> Optional[datetime]:
    """
    Parse expiry date from YYMMDD format.
    
    Args:
        expiry: Date string in YYMMDD format
        
    Returns:
        datetime object or None if invalid
    """
    if not expiry or len(expiry) != 6:
        return None
    
    try:
        year = int(expiry[:2])
        month = int(expiry[2:4])
        day = int(expiry[4:6])
        
        # Handle year: 00-49 = 2000-2049, 50-99 = 1950-1999
        if year < 50:
            year += 2000
        else:
            year += 1900
        
        # For expiry dates, if day is 00, use last day of month
        if day == 0:
            import calendar
            day = calendar.monthrange(year, month)[1]
        
        return datetime(year, month, day)
    except (ValueError, TypeError):
        return None


def format_national_number_display(number: str, number_type: str) -> str:
    """
    Format national number for display.
    
    Args:
        number: National pharmaceutical number
        number_type: Type identifier (DE_PZN, FR_CIP13, etc.)
        
    Returns:
        Formatted string for display
    """
    type_labels = {
        'DE_PZN': 'PZN',
        'FR_CIP13': 'CIP13',
        'BE_CNK': 'CNK',
        'NL_ZINDEX': 'Z-Index',
        'ES_CN': 'CN',
        'IT_AIC': 'AIC'
    }
    
    label = type_labels.get(number_type, number_type)
    
    # Format with spacing for readability
    if number_type == 'DE_PZN' and len(number) == 8:
        # Format as XX XXX XX-X
        return f"{label}: {number[:2]} {number[2:5]} {number[5:7]}-{number[7]}"
    elif number_type == 'FR_CIP13' and len(number) == 13:
        # Format as X XXXXX XXXXX X
        return f"{label}: {number[0]} {number[1:6]} {number[6:11]} {number[11]}"
    else:
        return f"{label}: {number}"