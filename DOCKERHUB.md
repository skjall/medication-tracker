# Medication Tracker

A lightweight Python-based web application that helps track medications, inventory levels, and prepare for hospital visits.

## Quick Reference

- **Maintained by**: [Jan Großheim](https://github.com/skjall)
- **GitHub**: [skjall/medication-tracker](https://github.com/skjall/medication-tracker)
- **Supported architectures**: `amd64`, `arm64`

## Features

- Medication management with detailed scheduling options
- Inventory tracking with low stock warnings
- Hospital visit planning with medication needs calculation
- Order management with printable forms
- Data import/export capabilities
- Timezone-aware operation
- Automatic inventory deduction

## Usage

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

## Docker Compose Example

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

## Environment Variables

- `SECRET_KEY`: Secret key for session signing (required in production)
- `FLASK_ENV`: Set to `production` for production use
- `LOG_LEVEL`: Set logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`)

## License

This project is licensed under the MIT License.