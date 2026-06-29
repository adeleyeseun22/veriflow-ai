from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from veriflow_api.api.dependencies.auth import DatabaseSession, require_workspace_roles
from veriflow_api.config import settings
from veriflow_api.contracts.search import SemanticSearchResponse
from veriflow_api.models.chunk import ChunkSourceType
from veriflow_api.models.workspace import WorkspaceMembership, WorkspaceRole
from veriflow_api.services.embeddings import EmbeddingProviderError
from veriflow_api.services.semantic_search import semantic_search

router = APIRouter(prefix="/workspaces/{workspace_id}/search")

WorkspaceReader = Annotated[
    WorkspaceMembership,
    Depends(require_workspace_roles(*list(WorkspaceRole))),
]


@router.get("/semantic", response_model=SemanticSearchResponse)
async def search_workspace_semantically(
    workspace_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
    query: Annotated[str, Query(alias="q", min_length=2, max_length=1000)],
    limit: Annotated[int, Query(ge=1, le=settings.semantic_search_max_limit)] = (
        settings.semantic_search_default_limit
    ),
    minimum_score: Annotated[float, Query(alias="min_score", ge=-1.0, le=1.0)] = 0.2,
    document_id: UUID | None = None,
    source_type: ChunkSourceType | None = None,
) -> SemanticSearchResponse:
    try:
        page = await semantic_search(
            session,
            workspace_id=workspace_id,
            query=query,
            limit=limit,
            minimum_score=minimum_score,
            document_id=document_id,
            source_type=source_type,
        )
    except EmbeddingProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return SemanticSearchResponse(
        query=query,
        provider=page.provider,
        model=page.model,
        dimension=page.dimension,
        items=page.items,
        total=len(page.items),
    )
