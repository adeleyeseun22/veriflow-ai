from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.config import settings
from veriflow_api.models.chunk import ChunkSourceType, DocumentChunk
from veriflow_api.models.document import Document
from veriflow_api.models.parsed_content import DocumentPage, DocumentSection, DocumentTable

CHUNKER_NAME = "veriflow-structure-aware"
CHUNKER_VERSION = "1.0"


@dataclass(slots=True)
class GeneratedChunk:
    source_type: ChunkSourceType
    source_label: str | None
    heading_path: list[str]
    page_start: int | None
    page_end: int | None
    content: str
    overlap_chars: int
    fingerprint: str
    section_id: UUID | None = None
    table_id: UUID | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def token_estimate(self) -> int:
        return estimate_tokens(self.content)


def estimate_tokens(text: str) -> int:
    """Estimate tokens deterministically without requiring a model-specific tokenizer."""

    if not text:
        return 0
    character_estimate = math.ceil(len(text) / 4)
    word_estimate = math.ceil(len(text.split()) * 1.33)
    return max(1, character_estimate, word_estimate)


def stable_chunk_fingerprint(
    *,
    source_type: ChunkSourceType,
    source_ordinal: int,
    part_index: int,
    heading_path: list[str],
    page_start: int | None,
    page_end: int | None,
    content: str,
) -> str:
    payload = {
        "content": content,
        "heading_path": heading_path,
        "page_end": page_end,
        "page_start": page_start,
        "part_index": part_index,
        "source_ordinal": source_ordinal,
        "source_type": source_type.value,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def split_text_with_overlap(
    text: str,
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[tuple[str, int]]:
    """Split text near natural boundaries while retaining deterministic overlap."""

    cleaned = text.strip()
    if not cleaned:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")
    if len(cleaned) <= max_chars:
        return [(cleaned, 0)]

    chunks: list[tuple[str, int]] = []
    start = 0
    previous_end = 0
    text_length = len(cleaned)

    while start < text_length:
        hard_end = min(start + max_chars, text_length)
        end = hard_end

        if hard_end < text_length:
            minimum_break = start + max(max_chars // 2, 1)
            for separator in ("\n\n", "\n", ". ", "; ", ", ", " "):
                candidate = cleaned.rfind(separator, minimum_break, hard_end)
                if candidate != -1:
                    end = candidate + len(separator)
                    break

        if end <= start:
            end = hard_end

        content = cleaned[start:end].strip()
        if content:
            actual_overlap = max(0, previous_end - start)
            chunks.append((content, actual_overlap))

        if end >= text_length:
            break

        next_start = max(end - overlap_chars, start + 1)
        if next_start > start and not cleaned[next_start - 1].isspace():
            boundary = cleaned.rfind(" ", start + 1, next_start + 1)
            if boundary > start:
                next_start = boundary + 1

        previous_end = end
        start = next_start

    return chunks


def _section_heading_path(section: DocumentSection) -> list[str]:
    path = [str(item).strip() for item in section.section_path if str(item).strip()]
    if section.title:
        title = section.title.strip()
        if title and (not path or path[-1] != title):
            path.append(title)
    return path


def _build_text_chunks(
    *,
    source_type: ChunkSourceType,
    source_ordinal: int,
    source_label: str | None,
    heading_path: list[str],
    page_start: int | None,
    page_end: int | None,
    content: str,
    section_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> list[GeneratedChunk]:
    parts = split_text_with_overlap(
        content,
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
    )
    generated: list[GeneratedChunk] = []
    for part_index, (part, actual_overlap) in enumerate(parts):
        generated.append(
            GeneratedChunk(
                source_type=source_type,
                source_label=source_label,
                heading_path=heading_path,
                page_start=page_start,
                page_end=page_end,
                content=part,
                overlap_chars=actual_overlap,
                fingerprint=stable_chunk_fingerprint(
                    source_type=source_type,
                    source_ordinal=source_ordinal,
                    part_index=part_index,
                    heading_path=heading_path,
                    page_start=page_start,
                    page_end=page_end,
                    content=part,
                ),
                section_id=section_id,
                metadata={
                    **(metadata or {}),
                    "source_ordinal": source_ordinal,
                    "part_index": part_index,
                    "part_count": len(parts),
                },
            )
        )
    return generated


def _table_row_text(table: DocumentTable, row: list[str], row_number: int) -> str:
    values: list[str] = []
    width = max(len(table.column_names), len(row))
    for index in range(width):
        heading = (
            table.column_names[index]
            if index < len(table.column_names) and table.column_names[index]
            else f"Column {index + 1}"
        )
        value = row[index] if index < len(row) else ""
        values.append(f"{heading}: {value}")
    return f"Row {row_number}: " + " | ".join(values)


def _table_heading(table: DocumentTable) -> list[str]:
    heading: list[str] = []
    if table.source_label:
        heading.append(table.source_label)
    if table.title and (not heading or heading[-1] != table.title):
        heading.append(table.title)
    return heading


def _build_table_chunks(table: DocumentTable) -> list[GeneratedChunk]:
    heading_path = _table_heading(table)
    title_line = f"Table: {table.title}" if table.title else f"Table {table.ordinal + 1}"
    header_line = "Columns: " + " | ".join(table.column_names)
    prefix = "\n".join(line for line in (title_line, header_line) if line.strip())

    rows = table.rows
    if not rows:
        content = prefix.strip()
        if not content:
            return []
        return [
            GeneratedChunk(
                source_type=ChunkSourceType.TABLE,
                source_label=table.source_label or table.title,
                heading_path=heading_path,
                page_start=table.page_number,
                page_end=table.page_number,
                content=content,
                overlap_chars=0,
                fingerprint=stable_chunk_fingerprint(
                    source_type=ChunkSourceType.TABLE,
                    source_ordinal=table.ordinal,
                    part_index=0,
                    heading_path=heading_path,
                    page_start=table.page_number,
                    page_end=table.page_number,
                    content=content,
                ),
                table_id=table.id,
                section_id=table.section_id,
                metadata={
                    "source_ordinal": table.ordinal,
                    "part_index": 0,
                    "part_count": 1,
                    "row_start": None,
                    "row_end": None,
                },
            )
        ]

    batches: list[tuple[str, int, int, int]] = []
    start = 0
    while start < len(rows):
        selected: list[str] = []
        end = start
        while end < len(rows) and len(selected) < settings.chunk_table_max_rows:
            row_text = _table_row_text(table, rows[end], end + 1)
            candidate = "\n".join([prefix, *selected, row_text]).strip()
            if selected and len(candidate) > settings.chunk_max_chars:
                break
            selected.append(row_text)
            end += 1
            if len(candidate) >= settings.chunk_max_chars:
                break

        if end == start:
            selected.append(_table_row_text(table, rows[start], start + 1))
            end = start + 1

        batch_text = "\n".join([prefix, *selected]).strip()
        overlap_rows = 0 if start == 0 else min(settings.chunk_table_row_overlap, len(selected))
        batches.append((batch_text, start + 1, end, overlap_rows))

        if end >= len(rows):
            break
        start = max(end - settings.chunk_table_row_overlap, start + 1)

    generated: list[GeneratedChunk] = []
    total_parts = sum(
        max(
            1,
            len(
                split_text_with_overlap(
                    batch_text,
                    max_chars=settings.chunk_max_chars,
                    overlap_chars=settings.chunk_overlap_chars,
                )
            ),
        )
        for batch_text, _, _, _ in batches
    )
    part_index = 0
    for batch_text, row_start, row_end, overlap_rows in batches:
        pieces = split_text_with_overlap(
            batch_text,
            max_chars=settings.chunk_max_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        for piece, actual_overlap in pieces:
            generated.append(
                GeneratedChunk(
                    source_type=ChunkSourceType.TABLE,
                    source_label=table.source_label or table.title,
                    heading_path=heading_path,
                    page_start=table.page_number,
                    page_end=table.page_number,
                    content=piece,
                    overlap_chars=actual_overlap,
                    fingerprint=stable_chunk_fingerprint(
                        source_type=ChunkSourceType.TABLE,
                        source_ordinal=table.ordinal,
                        part_index=part_index,
                        heading_path=heading_path,
                        page_start=table.page_number,
                        page_end=table.page_number,
                        content=piece,
                    ),
                    table_id=table.id,
                    section_id=table.section_id,
                    metadata={
                        "source_ordinal": table.ordinal,
                        "part_index": part_index,
                        "part_count": total_parts,
                        "row_start": row_start,
                        "row_end": row_end,
                        "overlap_rows": overlap_rows,
                        "table_is_truncated": table.is_truncated,
                    },
                )
            )
            part_index += 1

    return generated


def build_document_chunks(
    *,
    pages: list[DocumentPage],
    sections: list[DocumentSection],
    tables: list[DocumentTable],
) -> list[GeneratedChunk]:
    chunks: list[GeneratedChunk] = []

    for section in sorted(sections, key=lambda item: item.ordinal):
        if not section.content.strip():
            continue
        chunks.extend(
            _build_text_chunks(
                source_type=ChunkSourceType.SECTION,
                source_ordinal=section.ordinal,
                source_label=section.title,
                heading_path=_section_heading_path(section),
                page_start=section.page_start,
                page_end=section.page_end,
                content=section.content,
                section_id=section.id,
                metadata={
                    "heading_level": section.heading_level,
                    "section_metadata": section.section_metadata,
                },
            )
        )

    if not chunks:
        for page in sorted(pages, key=lambda item: item.page_number):
            if not page.text_content.strip():
                continue
            chunks.extend(
                _build_text_chunks(
                    source_type=ChunkSourceType.PAGE,
                    source_ordinal=page.page_number,
                    source_label=f"Page {page.page_number}",
                    heading_path=[f"Page {page.page_number}"],
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content=page.text_content,
                    metadata={"page_metadata": page.page_metadata},
                )
            )

    for table in sorted(tables, key=lambda item: item.ordinal):
        chunks.extend(_build_table_chunks(table))

    return chunks


async def replace_document_chunks(
    session: AsyncSession,
    *,
    document: Document,
    chunks: list[GeneratedChunk],
    chunked_at: datetime,
) -> list[DocumentChunk]:
    await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    models = [
        DocumentChunk(
            document_id=document.id,
            section_id=chunk.section_id,
            table_id=chunk.table_id,
            ordinal=ordinal,
            source_type=chunk.source_type,
            source_label=chunk.source_label,
            heading_path=chunk.heading_path,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            content=chunk.content,
            char_count=chunk.char_count,
            word_count=chunk.word_count,
            token_estimate=chunk.token_estimate,
            overlap_chars=chunk.overlap_chars,
            fingerprint=chunk.fingerprint,
            chunk_metadata=chunk.metadata,
        )
        for ordinal, chunk in enumerate(chunks)
    ]
    session.add_all(models)

    total_tokens = sum(chunk.token_estimate for chunk in chunks)
    metadata = dict(document.document_metadata)
    metadata["chunking"] = {
        "chunker_name": CHUNKER_NAME,
        "chunker_version": CHUNKER_VERSION,
        "chunked_at": chunked_at.isoformat(),
        "chunk_count": len(chunks),
        "token_estimate": total_tokens,
        "max_chars": settings.chunk_max_chars,
        "overlap_chars": settings.chunk_overlap_chars,
        "table_max_rows": settings.chunk_table_max_rows,
        "table_row_overlap": settings.chunk_table_row_overlap,
    }
    document.document_metadata = metadata
    document.chunker_name = CHUNKER_NAME
    document.chunker_version = CHUNKER_VERSION
    document.chunked_at = chunked_at
    document.chunk_count = len(chunks)
    document.chunk_token_estimate = total_tokens

    return models
