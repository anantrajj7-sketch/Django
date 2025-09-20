
"""Views providing a django-data-wizard powered import interface."""
from __future__ import annotations

from typing import Any, Dict, List

from django.http import Http404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from data_wizard import importers
from data_wizard.sources import FileSource
from data_wizard.views import ImportWizard

from . import serializers


WizardConfig = Dict[str, Any]


def _wizard(
    label: str,
    serializer: type,
    *,
    description: str,
    help_text: str | None = None,
    title: str | None = None,
) -> WizardConfig:
    """Helper to build wizard metadata entries."""

    return {
        "slug": label,
        "serializer": serializer,
        "title": title or label.replace("_", " ").title(),
        "description": description,
        "help_text": help_text,
    }


WIZARDS: List[WizardConfig] = [
    _wizard(
        "farmers",
        serializers.FarmerSerializer,
        description="Import core farmer demographics and household composition records.",
        help_text="Each row should uniquely identify a farmer via the farmer_id column.",
        title="Farmer Profiles",
    ),
    _wizard(
        "land_holdings",
        serializers.LandHoldingSerializer,
        description="Bulk upload land parcel details including irrigation sources and coordinates.",
        title="Land Holdings",
    ),
    _wizard(
        "assets",
        serializers.AssetSerializer,
        description="Capture agricultural and household assets owned by each farmer.",
        title="Assets",
    ),
    _wizard(
        "crop_history",
        serializers.CropHistorySerializer,
        description="Historical crop production statistics such as area, yield and usage distribution.",
        title="Crop History",
    ),
    _wizard(
        "cost_of_cultivation",
        serializers.CostOfCultivationSerializer,
        description="Cost line items for each crop including quantity and expenditure.",
        title="Cost of Cultivation",
    ),
    _wizard(
        "weed_records",
        serializers.WeedRecordSerializer,
        description="Information about weed management practices, labour and chemical usage.",
        title="Weed Management",
    ),
    _wizard(
        "water_management",
        serializers.WaterManagementSerializer,
        description="Water source utilisation patterns, irrigation counts and costs.",
        title="Water Management",
    ),
    _wizard(
        "pest_disease",
        serializers.PestDiseaseRecordSerializer,
        description="Pest and disease management measures applied across seasons.",
        title="Pest & Disease",
    ),
    _wizard(
        "nutrient_management",
        serializers.NutrientManagementSerializer,
        description="Fertiliser and nutrient application for each crop and season.",
        title="Nutrient Management",
    ),
    _wizard(
        "income_from_crops",
        serializers.IncomeFromCropsSerializer,
        description="Gross and by-product income statistics for cultivated crops.",
        title="Income from Crops",
    ),
    _wizard(
        "enterprises",
        serializers.EnterpriseSerializer,
        description="Allied enterprises operated by the household and their production outputs.",
        title="Enterprises",
    ),
    _wizard(
        "annual_family_income",
        serializers.AnnualFamilyIncomeSerializer,
        description="Annual income contributions from agriculture and non-farm sources.",
        title="Annual Family Income",
    ),
    _wizard(
        "migration_records",
        serializers.MigrationRecordSerializer,
        description="Household migration patterns, reasons and remittance flows.",
        title="Migration",
    ),
    _wizard(
        "adaptation_strategies",
        serializers.AdaptationStrategySerializer,
        description="Awareness and adoption of climate adaptation practices.",
        title="Adaptation Strategies",
    ),
    _wizard(
        "financial_records",
        serializers.FinancialRecordSerializer,
        description="Financial inclusion indicators, access to credit and institutional support.",
        title="Financial Inclusion",
    ),
    _wizard(
        "consumption_patterns",
        serializers.ConsumptionPatternSerializer,
        description="Monthly consumption and procurement of agricultural produce.",
        title="Consumption Patterns",
    ),
    _wizard(
        "market_prices",
        serializers.MarketPriceSerializer,
        description="Market price realisation for crops across seasons.",
        title="Market Prices",
    ),
    _wizard(
        "irrigated_rainfed",
        serializers.IrrigatedRainfedSerializer,
        description="Breakdown of irrigated versus rainfed areas and crop calendars.",
        title="Irrigated vs Rainfed",
    ),
]


class ImportLandingView(TemplateView):
    """Landing page that lists all available import wizards."""

    template_name = "pmksy/home.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["wizards"] = [
            {
                **wizard,
                "url": reverse("pmksy:import-run", kwargs={"wizard_slug": wizard["slug"]}),
            }
            for wizard in WIZARDS
        ]
        return context


class BasePMKSYImportWizard(ImportWizard):
    """Shared configuration for all PMKSY import workflows."""

    sources = (FileSource,)
    importer_classes = (
        importers.CSVImporter,
        importers.ExcelImporter,
        importers.JSONImporter,
    )


class PMKSYImportWizard(BasePMKSYImportWizard):
    """Single entry point that delegates to the requested serializer."""

    wizard_slug: str
    success_url_name = "pmksy:home"

    @cached_property
    def _wizard_map(self) -> Dict[str, WizardConfig]:
        return {item["slug"]: item for item in WIZARDS}

    def get_serializer_class(self):  # type: ignore[override]
        slug = self.kwargs.get("wizard_slug")
        try:
            return self._wizard_map[slug]["serializer"]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise Http404("Unknown import wizard") from exc

    def get_wizard_name(self) -> str:  # pragma: no cover - thin wrapper
        wizard_slug = self.kwargs.get("wizard_slug")
        wizard = self._wizard_map.get(wizard_slug)
        if wizard is None:
            raise Http404("Unknown import wizard")
        return wizard["title"]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        wizard_slug = self.kwargs.get("wizard_slug")
        wizard = self._wizard_map.get(wizard_slug)
        if wizard is None:
            raise Http404("Unknown import wizard")
        context.update(
            {
                "wizard": wizard,
                "wizard_slug": wizard_slug,
            }
        )
        return context

    def get_success_url(self):  # pragma: no cover - simple redirect helper
        return reverse(self.success_url_name)
