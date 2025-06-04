# Hitchhiker's Guide to the Galaxy - Demo Data

This directory contains CSV files with demo data themed around "The Hitchhiker's Guide to the Galaxy" by Douglas Adams.

## Files Included

### 1. `physicians.csv`
- **Dr. Ford Prefect**: Galactic Medicine specialist from Betelgeuse
- **Dr. Zaphod Beeblebrox**: Former President of the Galaxy, specializes in multiple personalities
- **Dr. Marvin Android**: Treats existential depression with a brain the size of a planet
- **Dr. Slartibartfast**: Award-winning fjord designer and planetary medicine expert

### 2. `medications.csv`
14 galactic medications including:
- **Pan Galactic Gargle Blaster**: Monthly cocktail (CRITICAL stock scenario)
- **Babel Fish**: Daily universal translator (CRITICAL - only 1 left!)
- **Heart of Gold Pills**: Infinite improbability capsules (LOW stock)
- **Vogon Poetry Antidote**: Emergency sanity preserver (MEDIUM stock)
- **Deep Thought Supplements**: Computational enhancement (GOOD stock)
- **Magrathea Sleep Aid**: For 5-million-year projects (EXCELLENT stock)

### 3. `inventory.csv`
Stock levels designed to demonstrate various scenarios:
- **CRITICAL**: Babel Fish (1 day supply), Pan Galactic Gargle Blaster (60 days at monthly dose)
- **LOW**: Jynnan Tonnyx (7.5 days), Heart of Gold Pills (12.5 days)
- **MEDIUM**: Vogon Poetry Antidote, Towel Fiber Extract
- **GOOD**: Deep Thought Supplements, SEP Field, Restaurant Digestion Aid
- **EXCELLENT**: Magrathea Sleep Aid (42+ days supply)

### 4. `physician_visits.csv`
- **Past visit**: Dr. Ford Prefect check-up at Milliways
- **Future visits**: Dr. Zaphod (42 days), Dr. Marvin (84 days), Dr. Slartibartfast (130 days)

### 5. `schedules.csv`
Realistic medication schedules:
- Daily medications with various time patterns
- Weekly medications (Total Perspective Vortex Shield, Guide Updates)
- Monthly medication (Pan Galactic Gargle Blaster)
- Emergency-only medication (Vogon Poetry Antidote)

### 6. `orders.csv`
Sample medication orders:
- **Current order for Dr. Zaphod**: Gap coverage and next-but-one planning items
- **Future order for Dr. Marvin**: Depression treatment supplies
- **Completed past order for Dr. Ford**: Celebration and travel supplies

## Import Instructions

1. Go to **Settings** > **Data Management** in your medication tracker
2. Import files in this order:
   1. **Physicians** first
   2. **Medications** second
   3. **Inventory** third
   4. **Visits** fourth
   5. **Schedules** fifth
   6. **Orders** last

## Demo Scenarios

After import, you'll be able to test:

### Gap Coverage Orders
- Several medications will run out before the 42-day visit to Dr. Zaphod
- Creates realistic gap coverage calculations

### Stock Level Alerts
- Critical medications needing immediate attention
- Low stock warnings for upcoming shortages
- Good stock levels that are sufficient

### Order Planning
- Standard orders for regular visits
- Next-but-one planning for Dr. Zaphod's visit
- Various tooltip calculations showing medication needs

### Automatic Deductions
- Most medications have auto-deduction enabled
- Realistic schedules for testing the deduction service

## Fun Features

- All medication names and descriptions contain Hitchhiker's references
- Physician specialties are galaxy-appropriate
- Visit intervals set to 42 days (the answer to everything)
- Package sizes include meaningful numbers (42, 84, etc.)
- Realistic but humorous medication notes

*Don't Panic! Your medication tracker is now loaded with the finest pharmaceutical products the galaxy has to offer.*

**Remember**: A towel is about the most massively useful thing an interstellar hitchhiker can have!