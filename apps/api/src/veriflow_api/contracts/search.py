from uuid import UUID

from pydantic import BaseModel, Field

from veriflow_api.models.chunk import ChunkSourceType


class SemanticSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    ordinal: int
    source_type: ChunkSourceType
    source_label: str | None
    heading_path: list[str]
    page_start: int | None
    page_end: int | None
    content: str
    fingerprint: str
    score: float = Field(ge=-1.0, le=1.0)
    distance: float = Field(ge=0.0, le=2.0)


class SemanticSearchResponse(BaseModel):
    query: str
    provider: str
    model: str
    dimension: int
    items: list[SemanticSearchResult]
    total: int
