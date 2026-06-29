from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veriflow_api.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from veriflow_api.models.document import Document
    from veriflow_api.models.parsed_content import DocumentSection, DocumentTable


class ChunkSourceType(StrEnum):
    SECTION = "section"
    PAGE = "page"
    TABLE = "table"


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_chunks_document_ordinal"),
        CheckConstraint("ordinal >= 0", name="nonnegative_ordinal"),
        CheckConstraint("char_count >= 0", name="nonnegative_char_count"),
        CheckConstraint("word_count >= 0", name="nonnegative_word_count"),
        CheckConstraint("token_estimate >= 0", name="nonnegative_token_estimate"),
        CheckConstraint("overlap_chars >= 0", name="nonnegative_overlap_chars"),
        CheckConstraint("char_length(fingerprint) = 64", name="valid_fingerprint_length"),
        Index("ix_document_chunks_document_source", "document_id", "source_type"),
        Index("ix_document_chunks_fingerprint", "fingerprint"),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    table_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_tables.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[ChunkSourceType] = mapped_column(
        Enum(ChunkSourceType, name="chunk_source_type", native_enum=True),
        nullable=False,
    )
    source_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heading_path: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_chars: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
    section: Mapped[DocumentSection | None] = relationship(
        "DocumentSection",
        back_populates="chunks",
    )
    table: Mapped[DocumentTable | None] = relationship(
        "DocumentTable",
        back_populates="chunks",
    )
