from uuid import uuid4

from veriflow_api.models.chunk import ChunkSourceType
from veriflow_api.models.parsed_content import DocumentPage, DocumentSection, DocumentTable
from veriflow_api.services.chunking import (
    build_document_chunks,
    estimate_tokens,
    split_text_with_overlap,
    stable_chunk_fingerprint,
)


def test_split_text_respects_size_and_adds_overlap() -> None:
    text = " ".join(f"word-{index}" for index in range(120))
    chunks = split_text_with_overlap(text, max_chars=180, overlap_chars=30)

    assert len(chunks) > 1
    assert all(len(content) <= 180 for content, _ in chunks)
    assert chunks[0][1] == 0
    assert any(overlap > 0 for _, overlap in chunks[1:])


def test_token_estimate_is_deterministic() -> None:
    text = "VeriFlow preserves evidence structure for reliable retrieval."
    assert estimate_tokens(text) == estimate_tokens(text)
    assert estimate_tokens(text) > 0
    assert estimate_tokens("") == 0


def test_chunk_fingerprint_is_stable_and_source_sensitive() -> None:
    arguments = {
        "source_type": ChunkSourceType.SECTION,
        "source_ordinal": 3,
        "part_index": 0,
        "heading_path": ["Results", "Coverage"],
        "page_start": 10,
        "page_end": 11,
        "content": "Coverage increased during the implementation period.",
    }
    first = stable_chunk_fingerprint(**arguments)
    second = stable_chunk_fingerprint(**arguments)
    changed = stable_chunk_fingerprint(**{**arguments, "part_index": 1})

    assert first == second
    assert first != changed
    assert len(first) == 64


def test_structure_aware_chunks_preserve_headings_pages_and_tables() -> None:
    document_id = uuid4()
    section_id = uuid4()
    table_id = uuid4()
    section = DocumentSection(
        id=section_id,
        document_id=document_id,
        ordinal=0,
        title="Coverage findings",
        heading_level=2,
        section_path=["Results", "Coverage findings"],
        content="Coverage increased across the supported implementation areas.",
        page_start=12,
        page_end=13,
        char_count=64,
        word_count=8,
        section_metadata={"section_type": "docx_heading"},
    )
    table = DocumentTable(
        id=table_id,
        document_id=document_id,
        section_id=section_id,
        ordinal=0,
        title="Coverage by state",
        source_label="Table 1",
        page_number=13,
        column_names=["State", "Coverage"],
        rows=[["Alpha", "82%"], ["Beta", "76%"]],
        row_count=2,
        column_count=2,
        is_truncated=False,
        table_metadata={},
    )

    chunks = build_document_chunks(pages=[], sections=[section], tables=[table])

    assert [chunk.source_type for chunk in chunks] == [
        ChunkSourceType.SECTION,
        ChunkSourceType.TABLE,
    ]
    assert chunks[0].heading_path == ["Results", "Coverage findings"]
    assert chunks[0].page_start == 12
    assert chunks[0].page_end == 13
    assert chunks[0].section_id == section_id
    assert chunks[1].table_id == table_id
    assert "State: Alpha" in chunks[1].content
    assert chunks[1].token_estimate > 0


def test_page_chunks_are_used_when_sections_have_no_text() -> None:
    document_id = uuid4()
    page = DocumentPage(
        id=uuid4(),
        document_id=document_id,
        page_number=4,
        text_content="A page-level fallback remains retrievable.",
        char_count=42,
        word_count=6,
        page_metadata={},
    )

    chunks = build_document_chunks(pages=[page], sections=[], tables=[])

    assert len(chunks) == 1
    assert chunks[0].source_type is ChunkSourceType.PAGE
    assert chunks[0].page_start == 4
    assert chunks[0].heading_path == ["Page 4"]
