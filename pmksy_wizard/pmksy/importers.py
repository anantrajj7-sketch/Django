"""Dataset definitions for powering CSV imports via django-data-wizard."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Sequence

from data_wizard import registry
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction
from itertable import load_file
from itertable.exceptions import ParseFailed

from . import models as pmksy_models


@dataclass
class Dataset:
    """Description of a dataset that can be imported."""

    key: str
    label: str
    description: str
    model: type[models.Model]
    required_columns: Sequence[str] = field(default_factory=tuple)
    field_map: Dict[str, str] = field(init=False)
    serializer_class: type | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.field_map = build_field_map(self.model)
        self.initialise_serializer()

    def initialise_serializer(self) -> None:
        """Register the model with data-wizard and cache the serializer."""

        try:
            registry.register(self.model)
        except ImproperlyConfigured:
            # Already registered – ignore to keep idempotent.
            pass
        self.serializer_class = registry.create_serializer(self.model)

    def humanised_column(self, column: str) -> str:
        """Return a user-friendly label for a column."""

        field_name = self.field_map.get(column, column)
        try:
            field = self.model._meta.get_field(field_name)
        except Exception:  # pragma: no cover - defensive fallback
            return column.replace("_", " ").title()

        verbose = field.verbose_name or field_name
        if isinstance(field, models.ForeignKey) and column.endswith("_id"):
            return f"{verbose} id".replace("_", " ").title()
        return verbose.replace("_", " ").title()

    @property
    def expected_columns(self) -> List[str]:
        return list(self.field_map.keys())

    @property
    def required(self) -> set[str]:
        return set(self.required_columns)


@dataclass
class ParsedRow:
    """A single row parsed from a tabular source."""

    line_number: int
    values: Dict[str, str]


@dataclass
class ParsedDataset:
    """Result of parsing a tabular file."""

    columns: List[str]
    original_headers: Dict[str, str]
    rows: List[ParsedRow]

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class RowError:
    """Details about an import failure."""

    row_number: int
    message: str
    values: Mapping[str, str]


@dataclass
class ImportSummary:
    """Summary returned after an import attempt."""

    total_rows: int
    created: int
    skipped: int
    errors: List[RowError]

    @property
    def error_count(self) -> int:
        return len(self.errors)


EMPTY_STRINGS = {"", "na", "n/a", "null", "none", "nil", "nan"}
BOOLEAN_TRUE = {"true", "1", "yes", "y", "t"}
BOOLEAN_FALSE = {"false", "0", "no", "n", "f"}
MAX_ERRORS_REPORTED = 50


def build_field_map(model: type[models.Model]) -> Dict[str, str]:
    """Derive a field mapping for a Django model."""

    mapping: Dict[str, str] = {}
    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False):
            continue
        if getattr(field, "auto_created", False):
            continue
        if isinstance(field, models.ForeignKey):
            mapping[f"{field.name}_id"] = field.name
        else:
            mapping[field.name] = field.name
    return mapping


def target_choices() -> List[tuple[str, str]]:
    """Return choices suitable for populating a form field."""

    return [(target.key, target.label) for target in TARGET_LIST]


def parse_uploaded_file(uploaded_file) -> ParsedDataset:
    """Parse an uploaded CSV file using the django-data-wizard stack."""

    uploaded_file.seek(0)
    if not getattr(uploaded_file, "name", None):
        uploaded_file.name = "upload.csv"

    try:
        iterator = load_file(uploaded_file)
    except ParseFailed as exc:  # pragma: no cover - exercised via validation
        raise ValueError(str(exc)) from exc

    columns = list(iterator.field_names)
    column_labels = {normalised: original for original, normalised in iterator.field_map.items()}

    rows: List[ParsedRow] = []
    for index, row in enumerate(iterator):
        values = row._asdict()
        line_number = iterator.start_row + index + 1
        rows.append(ParsedRow(line_number=line_number, values=values))

    return ParsedDataset(columns=columns, original_headers=column_labels, rows=rows)


class ModelImporter:
    """Perform imports for Django model datasets using DRF serializers."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset

    def import_rows(self, parsed_rows: Sequence[ParsedRow]) -> ImportSummary:
        created = 0
        skipped = 0
        errors: List[RowError] = []

        for parsed_row in parsed_rows:
            values = parsed_row.values
            if self._is_empty(values.values()):
                skipped += 1
                continue

            try:
                payload = self._prepare_payload(values)
            except ValueError as exc:
                self._append_error(errors, parsed_row, str(exc))
                continue

            serializer_class = self.dataset.serializer_class
            if serializer_class is None:  # pragma: no cover - defensive guard
                self.dataset.initialise_serializer()
                serializer_class = self.dataset.serializer_class

            serializer = serializer_class(data=payload)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        serializer.save()
                except Exception as exc:  # pragma: no cover - serializer handles validation
                    self._append_error(errors, parsed_row, str(exc))
                else:
                    created += 1
            else:
                message = format_serializer_errors(serializer.errors)
                self._append_error(errors, parsed_row, message)

        return ImportSummary(
            total_rows=len(parsed_rows),
            created=created,
            skipped=skipped,
            errors=errors,
        )

    def _prepare_payload(self, values: Mapping[str, str]) -> Dict[str, object]:
        for required in self.dataset.required:
            if self._is_empty([values.get(required)]):
                raise ValueError(f"Missing value for required column '{required}'")

        payload: Dict[str, object] = {}
        for column, field_name in self.dataset.field_map.items():
            if column not in values:
                continue
            raw_value = values[column]
            if self._is_empty([raw_value]):
                continue
            field = self.dataset.model._meta.get_field(field_name)
            try:
                payload[field.name] = convert_value(field, raw_value)
            except ValueError as exc:
                raise ValueError(f"Column '{column}': {exc}") from exc
        return payload

    @staticmethod
    def _append_error(errors: List[RowError], parsed_row: ParsedRow, message: str) -> None:
        if len(errors) >= MAX_ERRORS_REPORTED:
            return
        errors.append(
            RowError(
                row_number=parsed_row.line_number,
                message=message,
                values=dict(parsed_row.values),
            )
        )

    @staticmethod
    def _is_empty(values: Iterable[object | None]) -> bool:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                if value.strip() and value.strip().lower() not in EMPTY_STRINGS:
                    return False
            else:
                return False
        return True


def convert_value(field: models.Field, value: str) -> object:
    """Convert raw CSV values into Python objects suitable for serializers."""

    if isinstance(field, models.ForeignKey):
        target_field = field.target_field
        return convert_value(target_field, value)
    if isinstance(field, models.BooleanField):
        lowered = value.strip().lower()
        if lowered in BOOLEAN_TRUE:
            return True
        if lowered in BOOLEAN_FALSE:
            return False
        raise ValueError(f"Cannot interpret '{value}' as a boolean")
    if isinstance(field, models.UUIDField):
        return field.to_python(value)
    if isinstance(field, models.DecimalField):
        cleaned = value.replace(",", "")
        return field.to_python(cleaned)
    if isinstance(field, models.IntegerField):
        return field.to_python(value)
    if isinstance(field, models.FloatField):
        cleaned = value.replace(",", "")
        try:
            return float(cleaned)
        except ValueError as exc:  # pragma: no cover - handled via validation
            raise ValueError(str(exc)) from exc
    if isinstance(field, models.DateField):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError("Expected YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY date format")
    return value.strip()


def format_serializer_errors(errors) -> str:
    """Convert DRF serializer errors into a concise string."""

    if isinstance(errors, dict):
        parts = []
        for field, messages in errors.items():
            rendered = format_serializer_errors(messages)
            parts.append(f"{field}: {rendered}")
        return "; ".join(parts)
    if isinstance(errors, list):
        return ", ".join(format_serializer_errors(item) for item in errors)
    return str(errors)


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
        required_columns=required_cols,
    )
    IMPORT_TARGETS[key] = target
    TARGET_LIST.append(target)


def get_target(key: str) -> Dataset:
    """Retrieve the dataset configuration for a given key."""

    if key not in IMPORT_TARGETS:
        raise KeyError(f"Unknown import target '{key}'")
    return IMPORT_TARGETS[key]


def perform_import(target: Dataset, parsed_rows: Sequence[ParsedRow]) -> ImportSummary:
    """Delegate import execution to the serializer-backed importer."""

    importer = ModelImporter(target)
    return importer.import_rows(parsed_rows)
