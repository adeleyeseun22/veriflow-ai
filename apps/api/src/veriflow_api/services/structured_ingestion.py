from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.models.document import Document
from veriflow_api.models.parsed_content import DocumentPage, DocumentSection, DocumentTable
from veriflow_api.parsers.base import ParsedDocument


@dataclass(slots=True)
class StoredStructuredContent:
    pages: list[DocumentPage]
    sections: list[DocumentSection]
    tables: list[DocumentTable]


async def replace_structured_content(
    session: AsyncSession,
    *,
    document: Document,
    parsed: ParsedDocument,
    parsed_at: datetime,
) -> StoredStructuredContent:
    """Replace a document's extracted structure in one database transaction."""

    await session.execute(delete(DocumentTable).where(DocumentTable.document_id == document.id))
    await session.execute(delete(DocumentSection).where(DocumentSection.document_id == document.id))
    await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))

    page_models = [
        DocumentPage(
            document_id=document.id,
            page_number=page.page_number,
            text_content=page.text,
            char_count=page.char_count,
            word_count=page.word_count,
            page_metadata=page.metadata,
        )
        for page in parsed.pages
    ]
    session.add_all(page_models)

    section_models = [
        DocumentSection(
            document_id=document.id,
            ordinal=section.ordinal,
            title=section.title,
            heading_level=section.heading_level,
            section_path=section.section_path,
            content=section.content,
            page_start=section.page_start,
            page_end=section.page_end,
            char_count=section.char_count,
            word_count=section.word_count,
            section_metadata=section.metadata,
        )
        for section in parsed.sections
    ]
    session.add_all(section_models)
    await session.flush()

    section_ids = {section.ordinal: section.id for section in section_models}
    table_models = [
        DocumentTable(
            document_id=document.id,
            section_id=(
                section_ids.get(table.section_ordinal)
                if table.section_ordinal is not None
                else None
            ),
            ordinal=table.ordinal,
            title=table.title,
            source_label=table.source_label,
            page_number=table.page_number,
            column_names=table.column_names,
            rows=table.rows,
            row_count=table.row_count,
            column_count=table.column_count,
            is_truncated=table.is_truncated,
            table_metadata=table.metadata,
        )
        for table in parsed.tables
    ]
    session.add_all(table_models)
    await session.flush()

    metadata = dict(document.document_metadata)
    metadata["structured_ingestion"] = {
        "parser_name": parsed.parser_name,
        "parser_version": parsed.parser_version,
        "parsed_at": parsed_at.isoformat(),
        "page_count": len(parsed.pages),
        "section_count": len(parsed.sections),
        "table_count": len(parsed.tables),
        "extracted_text_chars": parsed.extracted_text_chars,
        "parser_metadata": parsed.metadata,
    }
    document.document_metadata = metadata
    document.parser_name = parsed.parser_name
    document.parser_version = parsed.parser_version
    document.parsed_at = parsed_at
    document.page_count = len(parsed.pages)
    document.section_count = len(parsed.sections)
    document.table_count = len(parsed.tables)
    document.extracted_text_chars = parsed.extracted_text_chars

    return StoredStructuredContent(
        pages=page_models,
        sections=section_models,
        tables=table_models,
    )
