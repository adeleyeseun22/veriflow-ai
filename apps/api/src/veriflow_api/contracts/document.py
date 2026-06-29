from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from veriflow_api.models.document import DocumentStatus


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
