from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ParserError(RuntimeError):
    """Raised when a supported document cannot be parsed safely."""


@dataclass(slots=True)
class ParsedPage:
    page_number: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(slots=True)
class ParsedSection:
    ordinal: int
    title: str | None
    content: str
    heading_level: int | None = None
    section_path: list[str] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass(slots=True)
class ParsedTable:
    ordinal: int
    title: str | None
    source_label: str | None
    column_names: list[str]
    rows: list[list[str]]
    row_count: int
    column_count: int
    is_truncated: bool = False
    page_number: int | None = None
    section_ordinal: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    parser_name: str
    parser_version: str
    pages: list[ParsedPage] = field(default_factory=list)
    sections: list[ParsedSection] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def extracted_text_chars(self) -> int:
        if self.pages:
            return sum(page.char_count for page in self.pages)
        return sum(section.char_count for section in self.sections)


class DocumentParser(Protocol):
    name: str
    version: str
    extensions: frozenset[str]

    def parse(self, path: Path) -> ParsedDocument: ...
