"""Tests for the PMKSY wizard and bulk import workflow."""
from __future__ import annotations

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import importers, models


class SurveyWizardViewTests(TestCase):
    """Ensure the survey wizard renders and persists data across steps."""

    def management_form_data(self, prefix: str, total: int) -> dict[str, str]:
        return {
            f"{prefix}-TOTAL_FORMS": str(total),
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def submit_farmer_step(self) -> None:
        data = {
            "name": "Asha",
            "farming_experience_years": "0",
            "family_males": "0",
            "family_females": "0",
            "family_children": "0",
            "family_adult": "0",
        }
        response = self.client.post(reverse("pmksy:wizard"), data)
        self.assertRedirects(response, reverse("pmksy:wizard-step", args=("land",)))

    def test_get_home_renders_first_step(self) -> None:
        response = self.client.get(reverse("pmksy:wizard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Farmer profile")
        self.assertContains(response, "Step 1 of")

    def test_post_farmer_creates_record_and_redirects(self) -> None:
        self.submit_farmer_step()
        self.assertEqual(models.Farmer.objects.count(), 1)
        farmer = models.Farmer.objects.get()
        self.assertEqual(farmer.name, "Asha")

    def test_land_step_persists_related_records(self) -> None:
        self.submit_farmer_step()

        data: dict[str, str] = {}
        data.update(self.management_form_data("land_holdings", 1))
        data.update(
            {
                "land_holdings-0-category": "Irrigated",
                "land_holdings-0-total_area_ha": "2.5",
                "land_holdings-0-irrigated_area_ha": "",
                "land_holdings-0-irrigation_source": "",
                "land_holdings-0-irrigation_no": "",
                "land_holdings-0-irrigation_latitude": "",
                "land_holdings-0-irrigation_longitude": "",
                "land_holdings-0-soil_details": "",
            }
        )
        data.update(self.management_form_data("assets", 0))

        response = self.client.post(reverse("pmksy:wizard-step", args=("land",)), data)
        self.assertRedirects(response, reverse("pmksy:wizard-step", args=("production",)))

        holding = models.LandHolding.objects.get()
        self.assertEqual(holding.category, "Irrigated")
        self.assertEqual(str(holding.farmer.farmer_id), str(models.Farmer.objects.get().farmer_id))

    def test_complete_wizard_renders_success_template(self) -> None:
        self.submit_farmer_step()

        # Land & assets step
        land_data: dict[str, str] = {}
        land_data.update(self.management_form_data("land_holdings", 1))
        land_data.update(
            {
                "land_holdings-0-category": "Rainfed",
                "land_holdings-0-total_area_ha": "1.5",
                "land_holdings-0-irrigated_area_ha": "",
                "land_holdings-0-irrigation_source": "",
                "land_holdings-0-irrigation_no": "",
                "land_holdings-0-irrigation_latitude": "",
                "land_holdings-0-irrigation_longitude": "",
                "land_holdings-0-soil_details": "",
            }
        )
        land_data.update(self.management_form_data("assets", 0))
        self.client.post(reverse("pmksy:wizard-step", args=("land",)), land_data)

        # Production step
        production_data: dict[str, str] = {}
        production_data.update(self.management_form_data("crop_history", 1))
        production_data.update(
            {
                "crop_history-0-crop_name": "Wheat",
                "crop_history-0-variety": "",
                "crop_history-0-season": "",
                "crop_history-0-area_ha": "",
                "crop_history-0-production_kg": "",
                "crop_history-0-sold_market_kg": "",
                "crop_history-0-retained_seed_kg": "",
                "crop_history-0-home_consumption_kg": "",
            }
        )
        for prefix in [
            "cost_cultivation",
            "water_management",
            "pest_disease",
            "nutrient_management",
            "income_crops",
            "irrigated_rainfed",
        ]:
            production_data.update(self.management_form_data(prefix, 0))
        self.client.post(reverse("pmksy:wizard-step", args=("production",)), production_data)

        # Livelihoods step
        livelihoods_data: dict[str, str] = {}
        livelihoods_data.update(self.management_form_data("enterprises", 1))
        livelihoods_data.update(
            {
                "enterprises-0-enterprise_type": "Dairy",
                "enterprises-0-number": "1",
                "enterprises-0-production": "",
                "enterprises-0-home_consumption": "",
                "enterprises-0-sold_market": "",
                "enterprises-0-market_price": "",
            }
        )
        for prefix in ["annual_income", "consumption", "market_price"]:
            livelihoods_data.update(self.management_form_data(prefix, 0))
        self.client.post(reverse("pmksy:wizard-step", args=("livelihoods",)), livelihoods_data)

        # Resilience step with final save
        resilience_data: dict[str, str] = {
            "loan": "on",
            "loan_purpose": "Crop inputs",
        }
        resilience_data.update(self.management_form_data("migration", 1))
        resilience_data.update(
            {
                "migration-0-age_gender": "25M",
                "migration-0-reason": "Seasonal work",
                "migration-0-migration_type": "",
                "migration-0-remittance": "",
            }
        )
        resilience_data.update(self.management_form_data("adaptation", 1))
        resilience_data.update(
            {
                "adaptation-0-strategy": "Drip irrigation",
                "adaptation-0-aware": "on",
                "adaptation-0-adopted": "",
            }
        )

        response = self.client.post(
            reverse("pmksy:wizard-step", args=("resilience",)), resilience_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pmksy/wizard_done.html")
        self.assertContains(response, "Survey stored for")

        farmer = models.Farmer.objects.get()
        self.assertEqual(farmer.enterprises.count(), 1)
        self.assertEqual(farmer.migration_records.count(), 1)
        self.assertEqual(farmer.adaptation_strategies.count(), 1)
        self.assertEqual(models.FinancialRecord.objects.filter(farmer=farmer).count(), 1)


class BulkImportWizardTests(TestCase):
    """Integration tests covering the CSV import wizard endpoints."""

    def upload_csv(self, target: str, content: str) -> None:
        file = SimpleUploadedFile("upload.csv", content.encode("utf-8"))
        response = self.client.post(
            reverse("pmksy:import"),
            {"target": target, "data_file": file},
            follow=False,
        )
        self.assertRedirects(response, reverse("pmksy:import-preview"))

    def test_import_farmer_profile(self) -> None:
        self.upload_csv("farmers", "name,district\nAsha,Solapur\n")

        preview = self.client.get(reverse("pmksy:import-preview"))
        self.assertContains(preview, "Total rows detected")
        self.assertContains(preview, "Farmers (Basic Profile)")

        confirm = self.client.post(reverse("pmksy:import-preview"), {"confirm": "1"})
        self.assertContains(confirm, "Import summary")
        self.assertEqual(models.Farmer.objects.count(), 1)
        farmer = models.Farmer.objects.get()
        self.assertEqual(farmer.name, "Asha")
        self.assertEqual(farmer.district, "Solapur")

    def test_import_land_holding(self) -> None:
        farmer = models.Farmer.objects.create(name="Rahul")
        csv = f"farmer_id,category,total_area_ha\n{farmer.farmer_id},Irrigated,2.5\n"
        self.upload_csv("land_holdings", csv)

        response = self.client.post(reverse("pmksy:import-preview"), {"confirm": "1"})
        self.assertContains(response, "Import summary")
        holding = models.LandHolding.objects.get()
        self.assertEqual(str(holding.farmer.farmer_id), str(farmer.farmer_id))
        self.assertEqual(holding.category, "Irrigated")

    def test_missing_required_columns_blocks_import(self) -> None:
        self.upload_csv("land_holdings", "category\nIrrigated\n")
        preview = self.client.get(reverse("pmksy:import-preview"))
        self.assertContains(preview, "Missing required columns")

        response = self.client.post(reverse("pmksy:import-preview"), {"confirm": "1"})
        self.assertContains(response, "Required columns are missing")
        self.assertEqual(models.LandHolding.objects.count(), 0)


class ImporterFunctionTests(TestCase):
    """Lower level tests for the import helper functions."""

    def test_perform_import_reports_missing_foreign_key(self) -> None:
        target = importers.get_target("land_holdings")
        rows = [
            importers.ParsedRow(
                line_number=2,
                values={"farmer_id": str(uuid.uuid4()), "category": "Seasonal"},
            )
        ]
        summary = importers.perform_import(target, rows)
        self.assertEqual(summary.created, 0)
        self.assertEqual(summary.error_count, 1)
        self.assertIn("Invalid pk", summary.errors[0].message)

