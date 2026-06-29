from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class DocumentPage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
        CheckConstraint("page_number > 0", name="positive_page_number"),
        CheckConstraint("char_count >= 0", name="nonnegative_char_count"),
        CheckConstraint("word_count >= 0", name="nonnegative_word_count"),
        Index("ix_document_pages_document_page", "document_id", "page_number"),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    char_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    word_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    page_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped[Document] = relationship("Document", back_populates="pages")


class DocumentSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_sections"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_sections_document_ordinal"),
        CheckConstraint("ordinal >= 0", name="nonnegative_ordinal"),
        CheckConstraint("char_count >= 0", name="nonnegative_char_count"),
        CheckConstraint("word_count >= 0", name="nonnegative_word_count"),
        Index("ix_document_sections_document_ordinal", "document_id", "ordinal"),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heading_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    word_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    section_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped[Document] = relationship("Document", back_populates="sections")
    tables: Mapped[list[DocumentTable]] = relationship(
        "DocumentTable",
        back_populates="section",
    )


class DocumentTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_tables"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_tables_document_ordinal"),
        CheckConstraint("ordinal >= 0", name="nonnegative_ordinal"),
        CheckConstraint("row_count >= 0", name="nonnegative_row_count"),
        CheckConstraint("column_count >= 0", name="nonnegative_column_count"),
        Index("ix_document_tables_document_ordinal", "document_id", "ordinal"),
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
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_names: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    rows: Mapped[list[list[str]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    column_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    table_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped[Document] = relationship("Document", back_populates="tables")
    section: Mapped[DocumentSection | None] = relationship(
        "DocumentSection",
        back_populates="tables",
    )
