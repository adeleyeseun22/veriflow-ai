from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
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
    from veriflow_api.models.parsed_content import DocumentPage, DocumentSection, DocumentTable
    from veriflow_api.models.processing_job import DocumentProcessingJob
    from veriflow_api.models.user import User
    from veriflow_api.models.workspace import Workspace


class DocumentStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "sha256", name="uq_documents_workspace_sha256"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("char_length(sha256) = 64", name="valid_sha256_length"),
        CheckConstraint("processing_attempts >= 0", name="nonnegative_processing_attempts"),
        CheckConstraint("page_count >= 0", name="nonnegative_page_count"),
        CheckConstraint("section_count >= 0", name="nonnegative_section_count"),
        CheckConstraint("table_count >= 0", name="nonnegative_table_count"),
        CheckConstraint("extracted_text_chars >= 0", name="nonnegative_extracted_text_chars"),
        Index("ix_documents_workspace_created_at", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=True),
        nullable=False,
        default=DocumentStatus.PENDING,
        server_default=text("'PENDING'::document_status"),
        index=True,
    )
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    page_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    section_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    table_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    extracted_text_chars: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    storage_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="documents")
    uploaded_by: Mapped[User] = relationship("User", back_populates="documents_uploaded")
    processing_jobs: Mapped[list[DocumentProcessingJob]] = relationship(
        "DocumentProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentProcessingJob.created_at.desc()",
    )
    pages: Mapped[list[DocumentPage]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )
    sections: Mapped[list[DocumentSection]] = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSection.ordinal",
    )
    tables: Mapped[list[DocumentTable]] = relationship(
        "DocumentTable",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentTable.ordinal",
    )
