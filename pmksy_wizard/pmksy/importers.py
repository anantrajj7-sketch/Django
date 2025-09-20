"""Utility classes and helpers to power the CSV bulk import wizard."""
from __future__ import annotations

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Mapping, Sequence

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, models, transaction
from django.utils.text import capfirst

from . import models as pmksy_models

EMPTY_STRINGS = {"", "na", "n/a", "null", "none", "nil", "nan"}
BOOLEAN_TRUE = {"true", "1", "yes", "y", "t"}
BOOLEAN_FALSE = {"false", "0", "no", "n", "f"}
MAX_ERRORS_REPORTED = 50


@dataclass(frozen=True)
class ImportTarget:
    """Describes a dataset that can be imported through the wizard."""

    key: str
    label: str
    description: str
    model: type[models.Model]
    field_map: Mapping[str, str]
    required_columns: Sequence[str] = field(default_factory=tuple)

    def humanised_column(self, column: str) -> str:
        """Return a readable name for a column."""

        field_name = self.field_map.get(column, column)
        try:
            field = self.model._meta.get_field(field_name)
        except Exception:  # pragma: no cover - defensive
            return capfirst(column.replace("_", " "))

        label = field.verbose_name or field_name
        if isinstance(field, models.ForeignKey) and column.endswith("_id"):
            return capfirst(f"{label} id")
        return capfirst(label)

    @property
    def expected_columns(self) -> List[str]:
        return list(self.field_map.keys())

    @property
    def required(self) -> set[str]:
        return set(self.required_columns)


@dataclass
class ParsedRow:
    """A single row parsed from an uploaded file."""

    line_number: int
    values: Dict[str, str]


@dataclass
class ParsedDataset:
    """Result of parsing an uploaded CSV file."""

    columns: List[str]
    original_headers: Dict[str, str]
    rows: List[ParsedRow]

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class RowError:
    """Information about a row that failed to import."""

    row_number: int
    message: str
    values: Mapping[str, str]


@dataclass
class ImportSummary:
    """Summary statistics returned after attempting an import."""

    total_rows: int
    created: int
    skipped: int
    errors: List[RowError]

    @property
    def error_count(self) -> int:
        return len(self.errors)


def build_field_map(model: type[models.Model]) -> Dict[str, str]:
    """Derive a mapping of CSV columns → model field names for a model."""

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

IMPORT_TARGETS: Dict[str, ImportTarget] = {}
TARGET_LIST: List[ImportTarget] = []

for key, label, description, model, required_cols in TARGET_DEFINITIONS:
    target = ImportTarget(
        key=key,
        label=label,
        description=description,
        model=model,
        field_map=build_field_map(model),
        required_columns=required_cols,
    )
    IMPORT_TARGETS[key] = target
    TARGET_LIST.append(target)


def get_target(key: str) -> ImportTarget:
    """Retrieve the ImportTarget for a given key."""

    if key not in IMPORT_TARGETS:
        raise KeyError(f"Unknown import target '{key}'")
    return IMPORT_TARGETS[key]


def target_choices() -> List[tuple[str, str]]:
    """Return choices suitable for populating a form field."""

    return [(target.key, target.label) for target in TARGET_LIST]


def normalise_header(header: str) -> str:
    """Normalise header names to snake_case for matching."""

    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", header or "")
    cleaned = cleaned.strip("_").lower()
    return cleaned


def parse_uploaded_file(uploaded_file) -> ParsedDataset:
    """Parse an uploaded CSV file into structured rows."""

    raw_bytes = uploaded_file.read()
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Unable to decode file as UTF-8.") from exc

    stream = io.StringIO(decoded)
    sample = decoded[:1024]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(stream, dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("The file does not contain a header row.")

    header_map = {original: normalise_header(original) for original in reader.fieldnames if original is not None}
    normalised_to_original = {normal: original for original, normal in header_map.items()}
    columns = list(normalised_to_original.keys())

    rows: List[ParsedRow] = []
    for index, raw_row in enumerate(reader, start=2):
        normalised_row: Dict[str, str] = {}
        meaningful = False
        for original, normalised in header_map.items():
            value = raw_row.get(original, "")
            if value is None:
                value = ""
            value = value.strip()
            if value:
                meaningful = True
            normalised_row[normalised] = value
        if not meaningful:
            continue
        rows.append(ParsedRow(line_number=index, values=normalised_row))

    if not rows:
        raise ValueError("No data rows were detected in the uploaded file.")

    return ParsedDataset(columns=columns, original_headers=normalised_to_original, rows=rows)


def is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        value = value.strip()
        return value.lower() in EMPTY_STRINGS if value else True
    return False


def parse_boolean(value: str) -> bool:
    lowered = value.lower()
    if lowered in BOOLEAN_TRUE:
        return True
    if lowered in BOOLEAN_FALSE:
        return False
    raise ValueError(f"Cannot interpret '{value}' as a boolean")


def parse_decimal(value: str) -> Decimal:
    try:
        cleaned = value.replace(",", "")
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot interpret '{value}' as a decimal") from exc


def parse_date(value: str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse '{value}' as a date (expected YYYY-MM-DD)")


def convert_value(field: models.Field, value: str):
    if isinstance(field, models.BooleanField):
        return parse_boolean(value)
    if isinstance(field, models.UUIDField):
        return uuid.UUID(value)
    if isinstance(field, models.DecimalField):
        return parse_decimal(value)
    if isinstance(field, (models.IntegerField, models.AutoField)):
        return int(value)
    if isinstance(field, models.FloatField):
        return float(value)
    if isinstance(field, models.DateField):
        return parse_date(value)
    return value


def prepare_row(target: ImportTarget, row: Mapping[str, str]) -> Dict[str, object] | None:
    """Convert a normalised CSV row into model keyword arguments."""

    if all(is_empty(value) for value in row.values()):
        return None

    for required in target.required:
        if is_empty(row.get(required)):
            raise ValueError(f"Missing value for required column '{required}'")

    cleaned: Dict[str, object] = {}
    for column, field_name in target.field_map.items():
        if column not in row:
            continue
        raw_value = row[column]
        if is_empty(raw_value):
            continue
        field = target.model._meta.get_field(field_name)
        if isinstance(field, models.ForeignKey):
            related_field = field.target_field
            try:
                related_value = convert_value(related_field, raw_value)
            except Exception as exc:  # pragma: no cover - handled via ValueError
                raise ValueError(str(exc)) from exc
            try:
                related_obj = field.remote_field.model.objects.get(
                    **{related_field.attname: related_value}
                )
            except ObjectDoesNotExist as exc:
                raise ValueError(
                    f"Related {field.remote_field.model.__name__} with {related_field.attname}={raw_value} not found"
                ) from exc
            cleaned[field.name] = related_obj
            continue
        try:
            cleaned[field.name] = convert_value(field, raw_value)
        except ValueError as exc:
            raise ValueError(f"Column '{column}': {exc}") from exc
    return cleaned


def perform_import(target: ImportTarget, parsed_rows: Sequence[ParsedRow]) -> ImportSummary:
    """Execute the import and return summary statistics."""

    created = 0
    skipped = 0
    errors: List[RowError] = []

    for parsed_row in parsed_rows:
        row_number = parsed_row.line_number
        values = parsed_row.values
        try:
            payload = prepare_row(target, values)
        except ValueError as exc:
            if len(errors) < MAX_ERRORS_REPORTED:
                errors.append(RowError(row_number=row_number, message=str(exc), values=dict(values)))
            continue

        if not payload:
            skipped += 1
            continue

        try:
            with transaction.atomic():
                instance = target.model(**payload)
                instance.full_clean()
                instance.save()
        except (ValidationError, IntegrityError) as exc:
            message = format_validation_error(exc)
            if len(errors) < MAX_ERRORS_REPORTED:
                errors.append(RowError(row_number=row_number, message=message, values=dict(values)))
        else:
            created += 1

    return ImportSummary(
        total_rows=len(parsed_rows),
        created=created,
        skipped=skipped,
        errors=errors,
    )


def format_validation_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        if hasattr(error, "message_dict"):
            parts = []
            for field, messages in error.message_dict.items():
                joined = ", ".join(messages)
                parts.append(f"{field}: {joined}")
            return "; ".join(parts)
        return ", ".join(error.messages)
    return str(error)

