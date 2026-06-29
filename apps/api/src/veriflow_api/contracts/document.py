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
