"""Dataset definitions that plug PMKSY models into data-wizard helpers."""
from __future__ import annotations

from typing import Dict, List, Sequence

from data_wizard import (
    Dataset,
    ImportSummary,
    ModelImporter,
    ParsedDataset,
    ParsedRow,
    build_field_map,
    parse_csv,
)

from django.db import models

from . import models as pmksy_models

TARGET_DEFINITIONS: Sequence[tuple[str, str, str, type[models.Model], Sequence[str]]] = [
    (
        "farmers",
        "Farmers (Basic Profile)",
        "Create farmer records with demographic and household level attributes.",
        pmksy_models.Farmer,
        ("name",),
    ),
    (
        "land_holdings",
        "Land Holdings",
        "Attach land parcel information to an existing farmer via farmer_id.",
        pmksy_models.LandHolding,
        ("farmer_id",),
    ),
    (
        "assets",
        "Assets",
        "Bulk upload asset ownership for farmers.",
        pmksy_models.Asset,
        ("farmer_id", "item_name"),
    ),
    (
        "crop_history",
        "Crop History",
        "Historical crop production information.",
        pmksy_models.CropHistory,
        ("farmer_id", "crop_name"),
    ),
    (
        "cost_of_cultivation",
        "Cost of Cultivation",
        "Cost inputs for crop cultivation.",
        pmksy_models.CostOfCultivation,
        ("farmer_id", "crop_name", "particular"),
    ),
    (
        "weed_records",
        "Weeds",
        "Weed management records, linked to an existing farmer.",
        pmksy_models.WeedRecord,
        ("farmer_id",),
    ),
    (
        "water_management",
        "Water Management",
        "Water management practices including irrigation counts and costs.",
        pmksy_models.WaterManagement,
        ("farmer_id",),
    ),
    (
        "pest_disease",
        "Pest & Disease",
        "Pest and disease management entries for a farmer.",
        pmksy_models.PestDiseaseRecord,
        ("farmer_id", "pest_disease"),
    ),
    (
        "nutrient_management",
        "Nutrient Management",
        "Fertiliser and nutrient application by crop and season.",
        pmksy_models.NutrientManagement,
        ("farmer_id", "crop_name"),
    ),
    (
        "income_from_crops",
        "Income from Crops",
        "Income realisation per crop and season.",
        pmksy_models.IncomeFromCrops,
        ("farmer_id", "crop_name"),
    ),
    (
        "enterprises",
        "Enterprises",
        "Allied enterprises and diversification activities.",
        pmksy_models.Enterprise,
        ("farmer_id", "enterprise_type"),
    ),
    (
        "annual_family_income",
        "Annual Family Income",
        "Annual income from different livelihood sources.",
        pmksy_models.AnnualFamilyIncome,
        ("farmer_id", "source"),
    ),
    (
        "migration",
        "Migration",
        "Migration details for household members.",
        pmksy_models.MigrationRecord,
        ("farmer_id", "age_gender"),
    ),
    (
        "adaptation_strategies",
        "Adaptation Strategies",
        "Climate adaptation strategies known or adopted.",
        pmksy_models.AdaptationStrategy,
        ("farmer_id", "strategy"),
    ),
    (
        "financials",
        "Financial Records",
        "Financial inclusion, credit and benefit utilisation.",
        pmksy_models.FinancialRecord,
        ("farmer_id",),
    ),
    (
        "consumption_pattern",
        "Consumption Pattern",
        "Monthly consumption of agricultural produce.",
        pmksy_models.ConsumptionPattern,
        ("farmer_id", "crop"),
    ),
    (
        "market_price",
        "Market Price",
        "Market price realisation for crops.",
        pmksy_models.MarketPrice,
        ("farmer_id", "crop"),
    ),
    (
        "irrigated_rainfed",
        "Irrigated & Rainfed",
        "Split irrigated versus rainfed crop areas.",
        pmksy_models.IrrigatedRainfed,
        ("farmer_id", "crop"),
    ),
]

IMPORT_TARGETS: Dict[str, Dataset] = {}
TARGET_LIST: List[Dataset] = []

for key, label, description, model, required_cols in TARGET_DEFINITIONS:
    target = Dataset(
        key=key,
        label=label,
        description=description,
        model=model,
        field_map=build_field_map(model),
        required_columns=required_cols,
    )
    IMPORT_TARGETS[key] = target
    TARGET_LIST.append(target)


def get_target(key: str) -> Dataset:
    """Retrieve the dataset configuration for a given key."""

    if key not in IMPORT_TARGETS:
        raise KeyError(f"Unknown import target '{key}'")
    return IMPORT_TARGETS[key]


def target_choices() -> List[tuple[str, str]]:
    """Return choices suitable for populating a form field."""

    return [(target.key, target.label) for target in TARGET_LIST]


def parse_uploaded_file(uploaded_file) -> ParsedDataset:
    """Parse an uploaded CSV file using the shared data-wizard parser."""

    uploaded_file.seek(0)
    return parse_csv(uploaded_file)


def perform_import(target: Dataset, parsed_rows: Sequence[ParsedRow]) -> ImportSummary:
    """Delegate import execution to the shared data-wizard importer."""

    importer = ModelImporter(target)
    return importer.import_rows(parsed_rows)
