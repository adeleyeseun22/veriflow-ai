from __future__ import annotations

import csv
from pathlib import Path

from veriflow_api.config import settings
from veriflow_api.parsers.base import ParsedDocument, ParsedSection, ParsedTable, ParserError
from veriflow_api.parsers.utils import (
    normalize_rows,
    rows_as_text,
    trim_empty_edges,
    unique_headers,
)


class CsvDocumentParser:
    name = "python-csv"
    version = "1.0"
    extensions = frozenset({"csv"})

    def parse(self, path: Path) -> ParsedDocument:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as source:
                sample = source.read(65536)
                source.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(source, dialect)
                collected: list[list[str]] = []
                truncated = False
                for row_index, row in enumerate(reader):
                    if row_index > settings.parser_max_table_rows:
                        truncated = True
                        break
                    collected.extend(normalize_rows([row]))
        except (UnicodeDecodeError, csv.Error, OSError) as error:
            raise ParserError("The CSV file could not be read as UTF-8 tabular data.") from error

        rows = trim_empty_edges(collected)
        if not rows:
            return ParsedDocument(
                parser_name=self.name,
                parser_version=self.version,
                sections=[
                    ParsedSection(
                        ordinal=0,
                        title=path.stem,
                        content="",
                        metadata={"section_type": "csv", "empty": True},
                    )
                ],
                metadata={"delimiter": getattr(dialect, "delimiter", ",")},
            )

        width = max(len(row) for row in rows)
        headers = unique_headers(rows[0], width)
        data_rows = [row + [""] * (width - len(row)) for row in rows[1:]]
        section = ParsedSection(
            ordinal=0,
            title=path.stem,
            content=rows_as_text(headers, data_rows),
            section_path=[path.stem],
            metadata={"section_type": "csv"},
        )
        table = ParsedTable(
            ordinal=0,
            title=path.stem,
            source_label="CSV data",
            column_names=headers,
            rows=data_rows,
            row_count=len(data_rows),
            column_count=width,
            is_truncated=truncated,
            section_ordinal=0,
            metadata={"delimiter": getattr(dialect, "delimiter", ",")},
        )
        return ParsedDocument(
            parser_name=self.name,
            parser_version=self.version,
            sections=[section],
            tables=[table],
            metadata={"delimiter": getattr(dialect, "delimiter", ",")},
        )
