# Scanner and Inventory System - Final Design

## Overview
Mobile-first barcode scanner with hybrid inventory tracking system that supports both legacy sum-based inventory and new package-based tracking simultaneously.

## 1. Scanner System

### DataMatrix Code Structure (GS1 Standard)
The 2D DataMatrix on German medication packages contains:
- `(01)` GTIN - Global Trade Item Number (14 digits)
- `(10)` Batch/Lot number
- `(17)` Expiry date (YYMMDD format)
- `(21)` Serial number (unique per package)

### Example Parse (German Product)
```
Raw: 010415013832707721100251263204341727013110403751B
Parsed:
- (01) 04150138327077 - GTIN
  - 0 = Packaging indicator/level
    - 0 = Base unit/item level (single package)
    - 1-8 = Different packaging hierarchies (e.g., carton, case, pallet)
    - 9 = Variable measure item
  - 415 = GS1 prefix (Germany: 400-440 range)
  - 013832707 = Company prefix + PZN (leading 0 + 8-digit PZN)
  - 7 = GTIN check digit
- (21) 10025126320434 - Serial Number (unique!)
- (17) 270131 - Expiry Date (2027-01-31)
- (10) 403751B - Batch Number

PZN extracted: 13832707 (positions 6-13 of GTIN)
```

### Country Detection and National Numbers
```python
def extract_national_number(gtin):
    """Extract national pharmaceutical number based on country"""
    prefix = gtin[1:4]  # GS1 prefix (3 digits after packaging indicator)
    
    # Germany (400-440)
    if 400 <= int(prefix) <= 440:
        return {
            'type': 'DE_PZN',
            'number': gtin[6:14],  # PZN at positions 6-13 (8 digits)
            'country': 'DE',
            'validation': validate_de_pzn
        }
    
    # France (300-379)
    elif 300 <= int(prefix) <= 379:
        return {
            'type': 'FR_CIP13',
            'number': gtin[1:14],  # Full GTIN is CIP13
            'country': 'FR',
            'validation': validate_fr_cip13
        }
    
    # Belgium/Luxembourg (540-549)
    elif 540 <= int(prefix) <= 549:
        return {
            'type': 'BE_CNK',
            'number': extract_be_cnk(gtin),
            'country': 'BE',
            'validation': validate_be_cnk
        }
    
    # Austria (900-919)
    elif 900 <= int(prefix) <= 919:
        return {
            'type': 'AT_PHARMANUMMER',
            'number': extract_at_pharmanummer(gtin),
            'country': 'AT',
            'validation': validate_at_pharmanummer
        }
    
    # Default - no national number
    return {
        'type': 'GTIN_ONLY',
        'number': gtin,
        'country': 'UNKNOWN',
        'validation': validate_gtin
    }
```

### Validation Functions

#### GTIN Check Digit (Modulo-10)
```python
def validate_gtin(gtin):
    """Validate GTIN-14 check digit using modulo-10 algorithm"""
    if len(gtin) != 14:
        return False
    
    total = 0
    for i, digit in enumerate(gtin[:-1]):
        multiplier = 3 if i % 2 == 0 else 1
        total += int(digit) * multiplier
    
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit) == gtin[-1]
```

#### German PZN Check Digit (Modulo-11)
```python
def validate_de_pzn(pzn):
    """Validate German PZN check digit using modulo-11 algorithm"""
    if len(pzn) != 8:
        return False
    
    weights = [2, 3, 4, 5, 6, 7, 8]
    total = sum(int(pzn[i]) * weights[i] for i in range(7))
    
    check_digit = total % 11
    if check_digit == 10:
        return False  # Invalid PZN
    
    return str(check_digit) == pzn[-1]
```

## 2. Database Schema

### Existing Tables (unchanged)
```sql
medications:
- id
- name
- physician_id
- aut_idem
- package_size_n1/n2/n3 (quantities)
+ inventory_mode ENUM('legacy', 'packages', 'hybrid') DEFAULT 'legacy'

inventory: (completely unchanged!)
- id
- medication_id
- current_count (sum of all units - legacy system)
```

### New Tables

#### `medication_packages` - Package Definitions
```sql
medication_packages:
- id
- medication_id (FK)
- package_size (N1/N2/N3/custom or country-specific)
- quantity (20, 50, 100, etc.)
- national_number (PZN for DE, CIP13 for FR, CNK for BE, etc.)
- national_number_type (DE_PZN, FR_CIP13, BE_CNK, AT_PHARMANUMMER, etc.)
- gtin (14 digits)
- country_code (DE, FR, BE, AT, etc.)
- created_at
- updated_at
```

#### `scanned_items` - Scan History
```sql
scanned_items:
- id
- medication_package_id (FK)
- gtin (full 14-digit GTIN from scan)
- national_number (extracted based on country)
- national_number_type (DE_PZN, FR_CIP13, BE_CNK, etc.)
- serial_number (UNIQUE - prevents duplicate scans!)
- batch_number
- expiry_date
- scanned_at
- scanned_by (user)
- order_item_id (optional - for order fulfillment)
- status (active, consumed, expired, returned)
- raw_data (complete DataMatrix string for future reference)
```

#### `package_inventory` - Active Package Tracking
```sql
package_inventory:
- id
- medication_id (FK)
- scanned_item_id (FK - links to scan data)
- current_units (adjustable! for inventory corrections)
- original_units (from package size)
- status ('sealed', 'open', 'consumed', 'expired')
- opened_at
- consumed_at
```

## 3. Hybrid Inventory System

### Core Concept
Both inventory systems run in parallel:
- **Legacy Inventory**: Sum-based total (existing system)
- **Package Inventory**: Individual packages with expiry dates

### Example State
```
Medication: Ibuprofen 400mg
├── Legacy Stock: 100 tablets (old inventory, no expiry data)
└── Package Stock: 150 tablets (3 scanned packages)
    ├── Package #1: 50 tablets (Exp: 2024-06, Status: OPEN)
    ├── Package #2: 50 tablets (Exp: 2024-08, Status: SEALED)
    └── Package #3: 50 tablets (Exp: 2025-01, Status: SEALED)

Total Available: 250 tablets
```

### Deduction Strategy
```python
def deduct_medication(medication_id, units_needed):
    # ALWAYS use legacy inventory FIRST (no expiry = use first)
    legacy_available = inventory.current_count
    
    if legacy_available >= units_needed:
        inventory.current_count -= units_needed
        return
    
    # Partial deduction from legacy
    units_needed -= legacy_available
    inventory.current_count = 0
    
    # Then deduct from packages (FEFO - First Expire First Out)
    packages = get_packages_by_expiry(medication_id)
    
    for package in packages:
        if package.status == 'sealed':
            package.status = 'open'
            package.opened_at = now()
        
        if units_needed <= package.current_units:
            package.current_units -= units_needed
            return
        else:
            units_needed -= package.current_units
            package.current_units = 0
            package.status = 'consumed'
```

## 4. User Workflows

### A. Scanning New Delivery
```
1. User receives medication delivery
2. Opens order or inventory page
3. Tap "Scan Package" → Camera opens
4. Scan package:
   - Parse DataMatrix
   - Validate GTIN & PZN checksums
   - Check serial number for duplicates
   - Create/find medication_package entry
   - Add to package_inventory
5. Continue scanning all packages
6. Total inventory updates automatically
```

### B. Manual Inventory (Traditional)
```
1. User goes to medication inventory
2. Click "Add Stock" (as before)
3. Enter total units manually
4. Updates legacy inventory count
5. No scanning required
```

### C. Inventory Adjustment Per Package
```
1. View package list for medication
2. Select specific package
3. Adjust count (absolute or relative)
4. Only affects that specific package
5. Reason logged for audit
```

## 5. Mode Management

### Three Inventory Modes

#### Legacy Mode (Default)
- Only manual entry
- No package tracking
- Current behavior preserved

#### Hybrid Mode
- Both systems active
- Legacy consumed first
- Then packages by expiry

#### Package Mode
- Only scanned packages
- No manual entry
- Full expiry tracking

### Mode Switching
```javascript
// Switch to Package-Only Mode
if (confirm("Delete legacy inventory (100 tablets)?")) {
    inventory.current_count = 0;
    medication.inventory_mode = 'packages';
}

// Switch to Legacy Mode
if (confirm("Delete all package data?")) {
    total = sum(packages.current_units);
    inventory.current_count = total;
    medication.inventory_mode = 'legacy';
    delete_all_packages();
}
```

## 6. Mobile Scanner Interface

### Progressive Web App (PWA)
- Manifest.json for "Add to Homescreen"
- Service Worker for offline capability
- Mobile-optimized camera interface

### Scanner UI
```
┌─────────────────────┐
│  ⬅ Inventory        │
├─────────────────────┤
│                     │
│   📷 Camera View    │
│  ┌─────────────┐    │
│  │ Scan Frame  │    │
│  └─────────────┘    │
│                     │
├─────────────────────┤
│ Last: Ibuprofen N2  │
│ Serial: ABC123 ✓    │
├─────────────────────┤
│ [Manual Entry]      │
└─────────────────────┘
```

## 7. Expiry Management

### Simple Dashboard Widget
```python
def get_expiring_medications(days_ahead=30):
    """Get all packages expiring within X days"""
    cutoff_date = datetime.now() + timedelta(days=days_ahead)
    return PackageInventory.query.join(ScannedItem).filter(
        ScannedItem.expiry_date <= cutoff_date,
        PackageInventory.status.in_(['sealed', 'open'])
    ).order_by(ScannedItem.expiry_date).all()
```

### Warning Levels
- 🔴 **Expired** (past date)
- 🟠 **Critical** (< 7 days)
- 🟡 **Warning** (< 30 days)
- 🟢 **OK** (> 30 days)

## 8. Special Cases

### Emergency Medications (EpiPen)
- Direct to package mode
- Individual tracking per pen
- Expiry alerts critical
- No automatic deduction

### Regular Daily Medications
- Often have legacy stock
- New deliveries scanned
- Seamless transition
- Legacy consumed first

## 9. Implementation Phases

### Phase 1: Core Scanner & Database
- [ ] Add new database tables
- [ ] Implement DataMatrix parser
- [ ] Add validation (GTIN/PZN)
- [ ] Store all scan data
- [ ] Duplicate detection

### Phase 2: Basic Integration
- [ ] Link scans to medications
- [ ] Display packages in UI
- [ ] Manual package adjustment
- [ ] Basic expiry display

### Phase 3: Hybrid Inventory
- [ ] Implement dual inventory display
- [ ] Smart deduction (legacy first)
- [ ] FEFO for packages
- [ ] Mode switching UI

### Phase 4: Mobile Optimization
- [ ] PWA setup
- [ ] Camera optimization
- [ ] Offline scanning
- [ ] Continuous scan mode

### Phase 5: Advanced Features
- [ ] Order fulfillment workflow
- [ ] Batch tracking
- [ ] Expiry notifications
- [ ] Analytics dashboard

## Key Benefits

### For Users
✅ **No forced migration** - Keep current workflow  
✅ **Gradual adoption** - Scan when ready  
✅ **Flexibility** - Manual or scanner or both  
✅ **Expiry tracking** - For scanned packages  
✅ **Inventory accuracy** - Per-package adjustments  

### For System
✅ **Backward compatible** - Nothing breaks  
✅ **Progressive enhancement** - Add features gradually  
✅ **Audit trail** - Complete scan history  
✅ **Data rich** - Store everything for future use  
✅ **Validation** - Checksum verification prevents errors