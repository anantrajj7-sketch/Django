
This Django project implements a multi-step data collection wizard for the PMKSY socio-economic survey schema documented in `pmksy_schema.md`.

## Features
- Session-backed form wizard that walks enumerators through farmer profile, land & assets, crop production, livelihood diversification and resilience data.
- Dynamic formsets for repeated sections such as land holdings, assets, crop history, cost of cultivation and more.
- SQLite database configuration out of the box with admin registrations for all models.
- Responsive UI with progressive enhancement for adding formset rows without reloading.

- CSV-driven bulk import wizard backed by the official [`data-wizard`](https://pypi.org/project/data-wizard/) package for ingesting data that already exists in spreadsheets following the PMKSY schema.


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

## Bulk import workflow
- Navigate to **Bulk import** from the header to launch the CSV wizard.
- Select the target dataset (e.g. Farmers, Land Holdings) and upload a UTF-8 CSV with headers that match the
  column names in `pmksy_schema.md`. When importing related tables, ensure each row includes the `farmer_id` of an existing
  farmer record.
- Review the automatic column matching, preview the first few rows and confirm the import. Validation errors are reported
  with row numbers so that source files can be amended before retrying.

## Data model
The models mirror the normalised tables described in `pmksy_schema.md`, covering farmer demographics, holdings, inputs, income sources, adaptation strategies and financial inclusion indicators.
