"""Importer primitives built for Django models."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Mapping, Sequence

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, models, transaction

from .tabular import Dataset, ImportSummary, ParsedRow, RowError

EMPTY_STRINGS = {"", "na", "n/a", "null", "none", "nil", "nan"}
BOOLEAN_TRUE = {"true", "1", "yes", "y", "t"}
BOOLEAN_FALSE = {"false", "0", "no", "n", "f"}
MAX_ERRORS_REPORTED = 50

__all__ = ["ModelImporter", "EMPTY_STRINGS", "MAX_ERRORS_REPORTED"]


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


class ModelImporter:
    """Perform imports for Django model datasets."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset

    def prepare_row(self, row: Mapping[str, str]) -> Dict[str, object] | None:
        if all(is_empty(value) for value in row.values()):
            return None

        for required in self.dataset.required:
            if is_empty(row.get(required)):
                raise ValueError(f"Missing value for required column '{required}'")

        cleaned: Dict[str, object] = {}
        for column, field_name in self.dataset.field_map.items():
            if column not in row:
                continue
            raw_value = row[column]
            if is_empty(raw_value):
                continue
            field = self.dataset.model._meta.get_field(field_name)
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

    def import_rows(self, parsed_rows: Sequence[ParsedRow]) -> ImportSummary:
        created = 0
        skipped = 0
        errors: list[RowError] = []

        for parsed_row in parsed_rows:
            row_number = parsed_row.line_number
            values = parsed_row.values
            try:
                payload = self.prepare_row(values)
            except ValueError as exc:
                if len(errors) < MAX_ERRORS_REPORTED:
                    errors.append(RowError(row_number=row_number, message=str(exc), values=dict(values)))
                continue

            if not payload:
                skipped += 1
                continue

            try:
                with transaction.atomic():
                    instance = self.dataset.model(**payload)
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
