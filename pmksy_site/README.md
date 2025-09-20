# PMKSY Survey Bulk Import Portal

This Django 5 project delivers a bulk data entry and import portal for the PMKSY socio-economic survey. It combines a spreadsheet import workflow powered by [`django-data-wizard`](https://github.com/wq/django-data-wizard) with a normalized relational schema ready for PostgreSQL.

## Features

- Spreadsheet import wizard at `/datawizard/` supporting Excel/CSV uploads and column mapping
- Normalized survey data model mirroring the PMKSY questionnaire
- UUID primary keys across all tables for safe synchronization
- Staff-only dashboard summarizing imports and quick links to admin & wizard
- Django admin configured with list filters, search, and CSV export actions
- Environment-aware database configuration (PostgreSQL for production, SQLite for quick start)

## Requirements

- Python 3.10+
- Django 5.x
- PostgreSQL 13+ (optional; SQLite enabled by default)
- Node.js is **not** required

## Installation

1. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```

2. **Install dependencies**

   ```bash
   pip install django==5.* djangorestframework django-filter django-data-wizard python-dotenv
   ```

3. **Configure environment variables**

   Copy `.env` (already provided) and adjust for PostgreSQL if desired. Leaving `DATABASE_ENGINE` blank keeps SQLite.

4. **Apply migrations & create a superuser**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run the development server**

   ```bash
   python manage.py runserver
   ```

   Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and log in using the superuser account. Only staff/superusers can reach the dashboard and data wizard.

## Import Workflow

1. Navigate to the dashboard (`/`).
2. Launch the Bulk Upload Wizard (link to `/datawizard/`).
3. Upload an Excel/CSV file and map columns to model fields.
4. Preview the data, run the import, and monitor status in the Recent Imports section.
5. Review imported records via the Django admin for exports or manual adjustments.

## Database Models

The `survey` app implements models for all major PMKSY data segments:

- Farmers, Land Holdings, Assets
- Crop History, Cost of Cultivation, Weed Management, Water Management
- Pest & Disease, Nutrient Management, Income from Crops
- Enterprises, Annual Family Income, Migration, Adaptation Strategies
- Financial Profiles, Consumption Patterns, Market Prices, Irrigated & Rainfed Plots

Each record uses a UUID primary key and is linked back to the `Farmer` profile with referential integrity.

## Optional Enhancements

- Enable PostgreSQL and configure backups for production deployments
- Extend with REST APIs or GIS validation using `djangorestframework` and spatial extensions
- Add audit trails using `django-simple-history`
- Schedule exports through Django management commands or cron jobs

## Running Tests & Checks

This starter project does not ship with automated tests yet. Run Django’s system checks once dependencies are installed:

```bash
python manage.py check
```

## License

This project is provided as-is for PMKSY survey data management initiatives.
