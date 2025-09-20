# PMKSY Bulk Import Portal

This Django project exposes a bulk import experience for the PMKSY socio-economic survey schema using
[`django-data-wizard`](https://github.com/wq/django-data-wizard). Instead of entering records manually, enumerators can upload
spreadsheets or CSV exports for each logical table listed in `pmksy_schema.md` and walk through a guided mapping wizard.

## Features
- Landing page that lists the full PMKSY schema broken down into importable datasets.
- `django-data-wizard` configured to accept CSV, XLSX and JSON files and persist them with Django REST Framework serializers.
- Rich styling to keep the focus on high-volume data onboarding instead of manual form filling.
- SQLite database configuration with admin registrations for quick inspection of imported rows.

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
4. Open `http://localhost:8000/` to choose a dataset and start the import wizard. Django admin is available at
   `http://localhost:8000/admin/` and the raw django-data-wizard interface is exposed at `http://localhost:8000/data-wizard/`.

## Configuring import templates
The wizard expects column names that match the serializer fields defined in `pmksy/serializers.py`. Consult
`pmksy_schema.md` for a canonical list of attributes and relationships. Files should contain UUID values for foreign keys so
that related records can be matched during import.

## Notes
The execution environment used for validation here does not ship with Django or django-data-wizard, therefore automated
checks cannot be executed. Follow the steps above in a local Python environment with network access to fully exercise the
application.
