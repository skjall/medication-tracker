# Medication Tracker

A lightweight Python-based web application hosted on Docker that helps track medications, inventory levels, and prepare for hospital visits.

## Features

- Medication management with dosage and frequency tracking
- Inventory tracking with warnings for low stock
- Hospital visit planning with medication needs calculation
- Package size optimization for prescription orders

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Installation

1. Clone this repository
2. Run `docker-compose up -d`
3. Access the application at http://localhost:8087

## Development

To set up a development environment:

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app/main.py`

## License

This project is licensed under the MIT License
