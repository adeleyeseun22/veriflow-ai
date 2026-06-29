from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from veriflow_api.config import settings


def normalize_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date, time)):
        rendered = value.isoformat()
    elif isinstance(value, Decimal):
        rendered = format(value, "f")
    else:
        rendered = str(value)
    rendered = rendered.replace("\x00", "").strip()
    return rendered[: settings.parser_max_cell_chars]


def normalize_rows(rows: Iterable[Iterable[Any]]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for row in rows:
        values = [serialize_cell(value) for value in row][: settings.parser_max_table_columns]
        normalized.append(values)
    return normalized


def trim_empty_edges(rows: list[list[str]]) -> list[list[str]]:
    while rows and not any(rows[-1]):
        rows.pop()
    if not rows:
        return []
    width = max(len(row) for row in rows)
    while width > 0 and all(len(row) < width or not row[width - 1] for row in rows):
        width -= 1
    return [row[:width] for row in rows]


def unique_headers(values: list[str], width: int) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index in range(width):
        base = (
            values[index].strip()
            if index < len(values) and values[index].strip()
            else f"Column {index + 1}"
        )
        count = seen.get(base, 0) + 1
        seen[base] = count
        headers.append(base if count == 1 else f"{base} ({count})")
    return headers


def rows_as_text(headers: list[str], rows: list[list[str]]) -> str:
    rendered = ["\t".join(headers)] if headers else []
    rendered.extend("\t".join(row) for row in rows)
    return "\n".join(rendered)[: settings.parser_max_section_chars]
