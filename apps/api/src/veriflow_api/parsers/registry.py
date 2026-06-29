from __future__ import annotations

from pathlib import Path

from veriflow_api.parsers.base import DocumentParser, ParsedDocument, ParserError
from veriflow_api.parsers.csv_parser import CsvDocumentParser
from veriflow_api.parsers.docx import DocxDocumentParser
from veriflow_api.parsers.pdf import PdfDocumentParser
from veriflow_api.parsers.xlsx import XlsxDocumentParser

PARSERS: tuple[DocumentParser, ...] = (
    PdfDocumentParser(),
    DocxDocumentParser(),
    XlsxDocumentParser(),
    CsvDocumentParser(),
)

PARSER_BY_EXTENSION = {extension: parser for parser in PARSERS for extension in parser.extensions}


def parser_for_extension(extension: str) -> DocumentParser:
    normalized = extension.lower().lstrip(".")
    parser = PARSER_BY_EXTENSION.get(normalized)
    if parser is None:
        raise ParserError(f"No structured parser is registered for .{normalized} files.")
    return parser


def parse_document(path: Path, extension: str) -> ParsedDocument:
    return parser_for_extension(extension).parse(path)
