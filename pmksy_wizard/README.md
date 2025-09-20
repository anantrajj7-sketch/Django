# PMKSY Survey Wizard

This Django project implements a multi-step data collection wizard for the PMKSY socio-economic survey schema documented in `pmksy_schema.md`.

## Features
- Session-backed form wizard that walks enumerators through farmer profile, land & assets, crop production, livelihood diversification and resilience data.
- Dynamic formsets for repeated sections such as land holdings, assets, crop history, cost of cultivation and more.
- SQLite database configuration out of the box with admin registrations for all models.
- Responsive UI with progressive enhancement for adding formset rows without reloading.

## Getting started
1. Install dependencies (requires Python 3.11):
   ```bash
   pip install -r requirements.txt
   ```
2. Apply migrations:
   ```bash
   python manage.py migrate
   ```
3. Run the development server:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
4. Open `http://localhost:8000/` to use the wizard. Django admin is available at `http://localhost:8000/admin/`.

## Data model
The models mirror the normalised tables described in `pmksy_schema.md`, covering farmer demographics, holdings, inputs, income sources, adaptation strategies and financial inclusion indicators.
