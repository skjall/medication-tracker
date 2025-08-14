# GS1 DataMatrix Parsing Documentation

## Overview
This document describes how pharmaceutical DataMatrix codes are parsed in the medication tracker system, with a focus on German PZN (Pharmazentralnummer) embedded in NTIN format.

## Example DataMatrix Code
```
010415013832707721100251263204341727013110403751B
```

## Parsing Breakdown

### Structure Analysis
The DataMatrix consists of concatenated Application Identifiers (AI) and their values:

| Position | AI | Value | Description |
|----------|-----|-------|-------------|
| 0-1 | 01 | - | Product Code (GTIN/NTIN) identifier |
| 2-15 | - | 04150138327077 | NTIN (14 digits) |
| 16-17 | 21 | - | Serial Number identifier |
| 18-31 | - | 10025126320434 | Serial Number (14 chars) |
| 32-33 | 17 | - | Expiry Date identifier |
| 34-39 | - | 270131 | Expiry Date (YYMMDD) |
| 40-41 | 10 | - | Batch/Lot Number identifier |
| 42-48 | - | 403751B | Batch Number (7 chars) |

### Detailed Parsing

```
01 04150138327077 21 10025126320434 17 270131 10 403751B
^^ ^^^^^^^^^^^^^^ ^^ ^^^^^^^^^^^^^^ ^^ ^^^^^^ ^^ ^^^^^^^
AI     NTIN       AI   Serial No.   AI Expiry AI  Batch
```

## NTIN (National Trade Item Number) Structure

The NTIN for German pharmaceutical products follows this structure:

```
0 4150 13832707 7
^ ^^^^ ^^^^^^^^ ^
| |    |        |
| |    |        +-- NTIN Check Digit (Modulo-10)
| |    +----------- PZN (8 digits)
| +---------------- GS1 Prefix for PZN (always 4150)
+------------------ Leading Zero (padding to 14 digits)
```

### Components:
1. **Leading Zero (0)**: Padding to make 14 digits total
2. **GS1 Prefix (4150)**: Fixed prefix assigned by GS1 Germany for PZN
3. **PZN (13832707)**: The 8-digit Pharmazentralnummer
4. **Check Digit (7)**: NTIN check digit (NOT the PZN check digit)

## Application Identifiers (AI)

| AI | Name | Format | Length | Description |
|----|------|--------|--------|-------------|
| 01 | GTIN/NTIN | Numeric | 14 (fixed) | Global/National Trade Item Number |
| 21 | Serial Number | Alphanumeric | Up to 20 (variable) | Unique serial number |
| 17 | Expiry Date | Numeric | 6 (fixed) | Format: YYMMDD |
| 10 | Batch/Lot | Alphanumeric | Up to 20 (variable) | Batch or lot number |

## Parsing Rules

### FNC1 Separator (Critical for Parsing)
The FNC1 character (ASCII 29, hex 0x1D) is used as a separator in GS1 barcodes:
- **Purpose**: Marks the end of variable-length fields
- **When Required**: After any variable-length field that is NOT the last element
- **Not Required**: After fixed-length fields or when variable field is last

### Fixed vs Variable Length Fields
- **Fixed Length**: AI 01 (14 digits), AI 17 (6 digits)
  - Parser knows exactly how many characters to read
  - No FNC1 needed after these fields
- **Variable Length**: AI 21 (serial), AI 10 (batch)
  - Can be 1-20 characters
  - MUST have FNC1 after them if another field follows
  - Without FNC1, parser cannot determine where field ends

### Serial Number Detection
The serial number in our example:
- Starts at position 18 (after "21")
- Ends at position 31 (before "17")
- Length: 14 characters
- Value: `10025126320434`

### Expiry Date Format
- Format: YYMMDD
- Example: `270131` = January 31, 2027
- Year interpretation:
  - 00-49 → 2000-2049
  - 50-99 → 1950-1999
- **Important Note (as of 2025)**: Day MUST be a valid day of the month (not "00")

### Batch Number
- Alphanumeric, variable length
- In our example: `403751B`
- Can contain letters and numbers

## PZN Extraction from NTIN

For German products with NTIN starting with `04150`:
1. Check if GTIN starts with `04150`
2. Extract positions 5-12 (8 digits)
3. This is the PZN

Example:
```
NTIN: 04150138327077
      ^^^^^--------
      |    |
      |    +-- PZN: 13832707
      +------- GS1 Prefix: 4150
```

## Validation

### NTIN Validation
The NTIN uses a Modulo-10 (Luhn) check digit:
- Calculate over first 13 digits
- Last digit is the check digit

### PZN Validation
PZN uses Modulo-11 check digit, but when embedded in NTIN:
- The PZN itself may or may not have a valid Modulo-11 check
- The NTIN check digit validates the entire number
- Trust the PZN if properly encoded in a valid NTIN

## Implementation Notes

### Parser Requirements
1. **Primary**: Check for FNC1 separators (ASCII 29) first
2. **Fallback**: Use sequential parsing for concatenated format without FNC1
3. Extract PZN from NTIN for German products
4. Respect maximum field lengths (20 chars for variable fields)

### Critical Parsing Challenges

#### The FNC1 Problem
Without FNC1 separators, the parser faces ambiguity:
```
Example: 2110025126320434172701311040375B
         ^^ AI 21 (serial)
           ^^^^^^^^^^^^^^ Where does serial end?
                         ^^ Could be AI 17 or part of serial!
```

#### Parser Strategy
1. **With FNC1**: Split on FNC1 characters for accurate field boundaries
2. **Without FNC1**: Use heuristics (look for known AI patterns after minimum field lengths)
3. **Limitation**: Serial numbers containing AI patterns (like "17" or "10") may be incorrectly parsed without FNC1

### Edge Cases
- Serial numbers can contain patterns that look like AIs (e.g., "10" or "17")
- Without FNC1, parser uses minimum field lengths before checking for next AI
- Some older codes might use different formats (PPN instead of NTIN)
- Maximum field lengths: Serial and Batch are limited to 20 characters

## Country-Specific Formats

### Germany (NTIN with PZN)
- NTIN prefix: `04150`
- Contains 8-digit PZN
- Most common for German pharmaceuticals

### Other European Countries
Different countries use different national number systems:
- France: CIP13 (13 digits)
- Belgium: CNK (7 digits)  
- Netherlands: Z-Index (7 digits)
- Spain: National Code (7 digits)
- Italy: AIC (9 digits)

Each has different GS1 prefixes and encoding rules.

## References
- [GS1 Germany - NTIN Guidelines](https://www.gs1-germany.de)
- [IFA - PZN to NTIN](http://www.ifaffm.de/de/ifa-codingsystem/)
- [EMVO - European Medicines Verification](https://emvo-medicines.eu)
- EU Falsified Medicines Directive (2011/62/EC)