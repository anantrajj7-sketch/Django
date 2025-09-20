"""Parsers for turning tabular data into structured rows."""
from __future__ import annotations

import csv
import io
import re
from typing import Dict, List

from .tabular import ParsedDataset, ParsedRow


__all__ = ["normalise_header", "parse_csv"]


def normalise_header(header: str) -> str:
    """Normalise a header to a snake_case identifier."""

    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", header or "")
    cleaned = cleaned.strip("_").lower()
    return cleaned


def parse_csv(uploaded_file) -> ParsedDataset:
    """Parse a CSV upload into a ParsedDataset."""

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
            if value not in ("", None):
                meaningful = True
            normalised_row[normalised] = value.strip() if isinstance(value, str) else value
        if not meaningful:
            continue
        rows.append(ParsedRow(line_number=index, values=normalised_row))

    if not rows:
        raise ValueError("No data rows were detected in the uploaded file.")

    return ParsedDataset(columns=columns, original_headers=normalised_to_original, rows=rows)
