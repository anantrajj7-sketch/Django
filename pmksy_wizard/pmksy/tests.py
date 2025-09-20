"""Tests for the PMKSY wizard and bulk import workflow."""
from __future__ import annotations

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import importers, models


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
        self.assertIn("Related", summary.errors[0].message)
