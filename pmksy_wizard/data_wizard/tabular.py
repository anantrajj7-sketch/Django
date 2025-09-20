"""Core data structures used by the import wizard."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence

from django.db import models
from django.utils.text import capfirst


@dataclass(frozen=True)
class Dataset:
    """Description of a dataset that can be imported."""

    key: str
    label: str
    description: str
    model: type[models.Model]
    field_map: Mapping[str, str]
    required_columns: Sequence[str] = field(default_factory=tuple)

    def humanised_column(self, column: str) -> str:
        """Return a user-friendly label for a column."""

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
