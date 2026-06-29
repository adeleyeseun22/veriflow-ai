from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from veriflow_api.models.document import DocumentStatus
from veriflow_api.models.processing_job import ProcessingJobStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    uploaded_by_id: UUID
    display_name: str
    original_filename: str
    file_extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    status_message: str | None
    processing_attempts: int
    parser_name: str | None
    parser_version: str | None
    parsed_at: datetime | None
    page_count: int
    section_count: int
    table_count: int
    extracted_text_chars: int
    storage_provider: str | None
    storage_bucket: str | None
    storage_key: str | None
    document_metadata: dict[str, object]
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class DuplicateDocumentResponse(BaseModel):
    duplicate: bool
    document: DocumentResponse | None = None


class DocumentProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    requested_by_id: UUID
    celery_task_id: str | None
    job_type: str
    status: ProcessingJobStatus
    attempts: int
    max_attempts: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    details: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DocumentProcessingJobListResponse(BaseModel):
    items: list[DocumentProcessingJobResponse]


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    page_number: int
    text_content: str
    char_count: int
    word_count: int
    page_metadata: dict[str, object]


class DocumentSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordinal: int
    title: str | None
    heading_level: int | None
    section_path: list[str]
    content: str
    page_start: int | None
    page_end: int | None
    char_count: int
    word_count: int
    section_metadata: dict[str, object]


class DocumentTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_id: UUID | None
    ordinal: int
    title: str | None
    source_label: str | None
    page_number: int | None
    column_names: list[str]
    rows: list[list[str]]
    row_count: int
    column_count: int
    is_truncated: bool
    table_metadata: dict[str, object]


class DocumentContentResponse(BaseModel):
    document: DocumentResponse
    pages: list[DocumentPageResponse]
    sections: list[DocumentSectionResponse]
    tables: list[DocumentTableResponse]
    returned_page_count: int
    returned_section_count: int
    returned_table_count: int
    table_row_limit: int
