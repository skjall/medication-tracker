# Medication Tracker

A lightweight Python-based web application that helps track medications, inventory levels, and prepare for hospital visits, using SQLite for data storage.

[![Docker Pulls](https://img.shields.io/docker/pulls/skjall/medication-tracker)](https://hub.docker.com/r/skjall/medication-tracker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Medication Management**:
  - Track medication dosage, frequency, and package sizes
  - Advanced scheduling options (daily, interval, or specific weekdays)
  - Automatic inventory deduction based on schedules

- **Inventory Tracking**:
  - Real-time inventory monitoring with low stock warnings
  - Package-based inventory management (N1, N2, N3 sizes)
  - Full history of inventory changes with timestamps

- **Hospital Visit Planning**:
  - Schedule and manage upcoming hospital visits
  - Calculate medication needs until next visit
  - Support for next-but-one visit planning

- **Order Management**:
  - Create medication orders for hospital visits
  - Calculate package requirements based on needs
  - Generate printable order forms
  - Track order fulfillment and update inventory

- **Data Management**:
  - Import/export data for all system components
  - CSV import/export for medications, inventory, visits, and orders
  - Database backup and optimization tools

## Access Warning

⚠️ **This software has no access protection. Users are advised to not expose any sensitive information and to only deploy it on local networks or behind appropriate security measures. The application is intended for personal use and should not be publicly accessible.**

## Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Medication Details
![Medication Details](screenshots/medication_details.png)

### Inventory Management
![Inventory Management](screenshots/inventory.png)

### Hospital Visits
![Hospital Visits](screenshots/visits.png)
```bash
docker run -d \
  --name medication-tracker \
  -p 8087:8087 \
  -v medication_tracker_data:/app/data \
  -v medication_tracker_logs:/app/logs \
  -e SECRET_KEY=your_secure_secret_key \
  skjall/medication-tracker:latest
```

Then access the application at http://localhost:8087

## Using Docker Compose

1. Create a docker-compose.yml file:

```yaml
version: '3.8'

services:
  medication-tracker:
    image: skjall/medication-tracker:latest
    container_name: medication-tracker
    ports:
      - '8087:8087'
    volumes:
      - medication_tracker_data:/app/data
      - medication_tracker_logs:/app/logs
    restart: unless-stopped
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=change_me_in_production
      - LOG_LEVEL=INFO

volumes:
  medication_tracker_data:
  medication_tracker_logs:
```

2. Start the application:

```bash
docker-compose up -d
```

3. Access the application at http://localhost:8087

## Environment Variables

- `SECRET_KEY`: Secret key for session signing (required in production)
- `FLASK_ENV`: Set to `production` for production use
- `LOG_LEVEL`: Set logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`)

## Data Persistence

All data is stored in SQLite databases in the `/app/data` directory. To persist your data, mount this directory as a volume.

## Usage Guide

### Adding Medications

1. Navigate to "Medications" → "Add Medication"
2. Enter medication details including name, dosage, package sizes
3. Set up medication schedules to define when and how much to take
4. Enable automatic deduction for seamless inventory management

### Managing Inventory

1. Navigate to "Inventory" → "Inventory Overview"
2. Use the quick adjust buttons to update inventory levels
3. View low stock warnings and depletion forecasts
4. Track inventory changes with detailed history logs

### Scheduling Hospital Visits

1. Navigate to "Hospital Visits" → "Schedule Visit"
2. Enter the date of your upcoming visit
3. Optionally create an order for the visit
4. Choose between regular ordering or next-but-one planning

### Creating Orders

1. Navigate to "Orders" → "New Order"
2. Select medications needed until your next visit
3. Review automatically calculated package requirements
4. Generate a printable order form for your hospital visit
5. Mark as fulfilled when medications are received to update inventory

## Building from Source

If you want to build the Docker image yourself:

```bash
git clone https://github.com/skjall/medication-tracker.git
cd medication-tracker
docker build -t medication-tracker --build-arg VERSION=$(cat version.txt) .
```

## Versioning

The application follows semantic versioning:

- Main branch: Uses explicit version from `version.txt` file
- Development branch: Auto-generates version with format `dev-YYYYMMDDHHMM-commit`
- Tagged releases: Use the tag version (e.g., `v1.0.0` → `1.0.0`)

To update the version:

```bash
# Increment patch version (1.0.0 → 1.0.1)
./scripts/update_version.sh patch

# Increment minor version (1.0.0 → 1.1.0)
./scripts/update_version.sh minor

# Increment major version (1.0.0 → 2.0.0)
./scripts/update_version.sh major

# Update, commit, and tag in one command
./scripts/update_version.sh patch --commit --tag
```

## Development Setup

To set up a development environment:

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app/main.py
   ```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.