"""
Barcode validation for various national pharmaceutical number formats.
"""

from typing import Optional, Tuple


def identify_barcode_format(barcode: str) -> Optional[Tuple[str, str]]:
    """
    Identify and validate standalone pharmaceutical barcode formats.
    
    Args:
        barcode: Clean barcode string (without special characters)
        
    Returns:
        Tuple of (national_number, number_type) or None if not recognized
    """
    if not barcode or not barcode.isdigit():
        return None
    
    length = len(barcode)
    
    # German PZN - 7 or 8 digits
    # Note: Many real-world PZNs have incorrect check digits, but we still accept them
    if length in [7, 8]:
        # Try strict validation first
        if validate_de_pzn(barcode):
            return (barcode, 'DE_PZN')
        # For 8-digit codes, assume PZN even if check digit is wrong
        # (common in practice)
        elif length == 8:
            return (barcode, 'DE_PZN')
    
    # French CIP7 - 7 digits
    if length == 7:
        # CIP7 doesn't have check digit validation
        # Could be PZN or CIP7, PZN validation failed above
        # So might be CIP7
        if not validate_de_pzn(barcode):
            return (barcode, 'FR_CIP7')
    
    # French CIP13 - 13 digits with Modulo-10 check
    if length == 13:
        if validate_fr_cip13(barcode):
            return (barcode, 'FR_CIP13')
    
    # Belgian CNK - 7 digits with Modulo-97 check
    if length == 7:
        if validate_be_cnk(barcode):
            return (barcode, 'BE_CNK')
    
    # Italian AIC - 9 digits
    if length == 9:
        # AIC format: 9 digits, no standard check digit
        return (barcode, 'IT_AIC')
    
    # Spanish National Code - 6 or 7 digits
    if length in [6, 7]:
        # Spanish codes don't have standard validation
        return (barcode, 'ES_CN')
    
    # Dutch Z-Index - 7 digits
    if length == 7:
        # Z-Index doesn't have check digit validation
        # Already checked PZN and CNK above
        return (barcode, 'NL_ZINDEX')
    
    return None


def validate_de_pzn(pzn: str) -> bool:
    """
    Validate German PZN with Modulo-11 check digit.
    PZN8: 8 digits total (7 digits + 1 check digit)
    
    Calculation:
    - 1st digit × 1
    - 2nd digit × 2
    - 3rd digit × 3
    - 4th digit × 4
    - 5th digit × 5
    - 6th digit × 6
    - 7th digit × 7
    - Sum modulo 11 = check digit (8th digit)
    """
    if not pzn or not pzn.isdigit():
        return False
    
    if len(pzn) == 8:
        # PZN8: Calculate check digit for first 7 digits
        total = 0
        for i in range(7):
            # Position starts at 1, not 0
            total += int(pzn[i]) * (i + 1)
        
        check = total % 11
        
        # If remainder is 10, this PZN is invalid (would need 2 digits)
        if check == 10:
            return False
            
        expected_check = int(pzn[7])
        return check == expected_check
    
    # Old PZN7 format (deprecated but might still exist)
    elif len(pzn) == 7:
        # PZN7: 6 digits + 1 check digit
        total = 0
        for i in range(6):
            total += int(pzn[i]) * (i + 2)  # Weights 2-7 for positions 1-6
        
        check = total % 11
        if check == 10:
            return False
            
        expected_check = int(pzn[6])
        return check == expected_check
    
    return False


def validate_fr_cip13(cip13: str) -> bool:
    """
    Validate French CIP13 with Modulo-10 (Luhn) check digit.
    """
    if not cip13 or len(cip13) != 13 or not cip13.isdigit():
        return False
    
    # Standard Modulo-10 (Luhn) validation
    total = 0
    for i in range(12):  # First 12 digits
        digit = int(cip13[i])
        if i % 2 == 0:  # Even position (0-indexed)
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(cip13[12])


def validate_be_cnk(cnk: str) -> bool:
    """
    Validate Belgian CNK with Modulo-97 check digit.
    CNK format: 7 digits total, first 5 are code, last 2 are check.
    """
    if not cnk or len(cnk) != 7 or not cnk.isdigit():
        return False
    
    # First 5 digits are the code, last 2 are check digits
    code = int(cnk[:5])
    check = int(cnk[5:7])
    
    # Modulo-97 validation
    expected = 97 - (code % 97)
    
    return check == expected


def format_barcode_display(number: str, number_type: str) -> str:
    """
    Format barcode for user-friendly display.
    """
    type_labels = {
        'DE_PZN': 'PZN',
        'FR_CIP7': 'CIP7',
        'FR_CIP13': 'CIP13',
        'BE_CNK': 'CNK',
        'NL_ZINDEX': 'Z-Index',
        'ES_CN': 'CN',
        'IT_AIC': 'AIC'
    }
    
    label = type_labels.get(number_type, number_type)
    return f"{label}: {number}"