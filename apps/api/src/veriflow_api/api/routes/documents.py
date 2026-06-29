from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from veriflow_api.api.dependencies.auth import DatabaseSession, require_workspace_roles
from veriflow_api.contracts.document import (
    DocumentListResponse,
    DocumentResponse,
    DuplicateDocumentResponse,
)
from veriflow_api.models.document import Document, DocumentStatus
from veriflow_api.models.workspace import WorkspaceMembership, WorkspaceRole
from veriflow_api.services.documents import find_duplicate_document

router = APIRouter(prefix="/workspaces/{workspace_id}/documents")

WorkspaceReader = Annotated[
    WorkspaceMembership,
    Depends(
        require_workspace_roles(
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
            WorkspaceRole.REVIEWER,
        )
    ),
]


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    workspace_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    filters = [Document.workspace_id == workspace_id]
    if document_status is not None:
        filters.append(Document.status == document_status)

    total = await session.scalar(select(func.count(Document.id)).where(*filters))
    documents = (
        await session.scalars(
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/check-duplicate", response_model=DuplicateDocumentResponse)
async def check_duplicate_document(
    workspace_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
    sha256: str = Query(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9A-Fa-f]{64}$",
    ),
) -> DuplicateDocumentResponse:
    document = await find_duplicate_document(
        session,
        workspace_id=workspace_id,
        sha256=sha256,
    )
    return DuplicateDocumentResponse(
        duplicate=document is not None,
        document=DocumentResponse.model_validate(document) if document is not None else None,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    workspace_id: UUID,
    document_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
) -> DocumentResponse:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentResponse.model_validate(document)
