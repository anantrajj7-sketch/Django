"""Local compatibility helpers for django-data-wizard 2.0."""
from __future__ import annotations

from typing import Any, Iterable


class BaseImporter:
    """Lightweight importer stub compatible with django-data-wizard settings."""

    slug = "base"
    label = "Base Importer"
    file_extensions: tuple[str, ...] = ()
    content_types: tuple[str, ...] = ()

    def __init__(self, source: Any | None = None):  # pragma: no cover - compatibility shim
        self.source = source

    def load_iter(self) -> Iterable[Any]:  # pragma: no cover - defensive default
        raise NotImplementedError("Bulk import uses pmksy.importers for file parsing.")


class CSVImporter(BaseImporter):
    slug = "csv"
    label = "CSV File"
    file_extensions = (".csv",)
    content_types = ("text/csv", "application/vnd.ms-excel")


class ExcelImporter(BaseImporter):
    slug = "excel"
    label = "Excel Workbook"
    file_extensions = (".xls", ".xlsx")
    content_types = (
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class JSONImporter(BaseImporter):
    slug = "json"
    label = "JSON Document"
    file_extensions = (".json",)
    content_types = ("application/json",)


__all__ = ["BaseImporter", "CSVImporter", "ExcelImporter", "JSONImporter"]
