from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from veriflow_api.config import settings
from veriflow_api.parsers.base import ParsedDocument, ParsedPage, ParsedSection, ParserError
from veriflow_api.parsers.utils import normalize_text


class PdfDocumentParser:
    name = "pypdf"
    version = "1.0"
    extensions = frozenset({"pdf"})

    def parse(self, path: Path) -> ParsedDocument:
        try:
            reader = PdfReader(str(path), strict=False)
        except (PdfReadError, OSError, ValueError) as error:
            raise ParserError("The PDF could not be opened for text extraction.") from error

        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception as error:
                raise ParserError("Password-protected PDFs are not supported.") from error
            if not unlocked:
                raise ParserError("Password-protected PDFs are not supported.")

        if len(reader.pages) > settings.parser_max_pdf_pages:
            raise ParserError(
                f"The PDF exceeds the {settings.parser_max_pdf_pages}-page parsing limit."
            )

        pages: list[ParsedPage] = []
        sections: list[ParsedSection] = []
        extraction_errors = 0

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = normalize_text(page.extract_text() or "")
            except Exception:
                text = ""
                extraction_errors += 1

            pages.append(
                ParsedPage(
                    page_number=page_number,
                    text=text,
                    metadata={"text_extracted": bool(text)},
                )
            )
            if text:
                sections.append(
                    ParsedSection(
                        ordinal=len(sections),
                        title=f"Page {page_number}",
                        content=text[: settings.parser_max_section_chars],
                        page_start=page_number,
                        page_end=page_number,
                        metadata={"section_type": "pdf_page"},
                    )
                )

        metadata = {
            "source_page_count": len(reader.pages),
            "text_extraction_errors": extraction_errors,
            "pdf_metadata": {
                str(key).lstrip("/"): str(value)[:2000]
                for key, value in (reader.metadata or {}).items()
                if value is not None
            },
            "table_extraction": "not_attempted",
        }
        return ParsedDocument(
            parser_name=self.name,
            parser_version=self.version,
            pages=pages,
            sections=sections,
            metadata=metadata,
        )
