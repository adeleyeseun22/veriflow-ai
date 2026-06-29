from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from veriflow_api.contracts.search import SemanticSearchResult
from veriflow_api.models.chunk import ChunkSourceType, DocumentChunk
from veriflow_api.models.document import Document
from veriflow_api.services.embeddings import EmbeddingProvider, get_embedding_provider


@dataclass(frozen=True, slots=True)
class SemanticSearchPage:
    provider: str
    model: str
    dimension: int
    items: list[SemanticSearchResult]


async def semantic_search(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    limit: int,
    minimum_score: float,
    document_id: UUID | None = None,
    source_type: ChunkSourceType | None = None,
    provider: EmbeddingProvider | None = None,
) -> SemanticSearchPage:
    active_provider = provider or get_embedding_provider()
    query_vector = await run_in_threadpool(active_provider.embed_query, query)

    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    filters = [
        Document.workspace_id == workspace_id,
        DocumentChunk.embedding.is_not(None),
        DocumentChunk.embedding_provider == active_provider.provider_name,
        DocumentChunk.embedding_model == active_provider.model_name,
        distance <= 1.0 - minimum_score,
    ]
    if document_id is not None:
        filters.append(DocumentChunk.document_id == document_id)
    if source_type is not None:
        filters.append(DocumentChunk.source_type == source_type)

    rows = (
        await session.execute(
            select(
                DocumentChunk,
                Document.original_filename.label("document_name"),
                distance.label("distance"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
            .order_by(distance.asc(), DocumentChunk.document_id, DocumentChunk.ordinal)
            .limit(limit)
        )
    ).all()

    items = [
        SemanticSearchResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=document_name,
            ordinal=chunk.ordinal,
            source_type=chunk.source_type,
            source_label=chunk.source_label,
            heading_path=chunk.heading_path,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            content=chunk.content,
            fingerprint=chunk.fingerprint,
            distance=max(0.0, min(2.0, float(row_distance))),
            score=max(-1.0, min(1.0, 1.0 - float(row_distance))),
        )
        for chunk, document_name, row_distance in rows
    ]
    return SemanticSearchPage(
        provider=active_provider.provider_name,
        model=active_provider.model_name,
        dimension=active_provider.dimension,
        items=items,
    )
