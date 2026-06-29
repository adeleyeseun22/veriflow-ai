from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from veriflow_api.api.dependencies.auth import (
    AuthContextDependency,
    DatabaseSession,
    require_workspace_roles,
    validate_csrf,
)
from veriflow_api.config import settings
from veriflow_api.contracts.document import (
    DocumentContentResponse,
    DocumentPageResponse,
    DocumentResponse,
    DocumentSectionResponse,
    DocumentTableResponse,
)
from veriflow_api.models.document import Document, DocumentStatus
from veriflow_api.models.parsed_content import DocumentPage, DocumentSection, DocumentTable
from veriflow_api.models.processing_job import DocumentProcessingJob, ProcessingJobStatus
from veriflow_api.models.workspace import WorkspaceMembership, WorkspaceRole
from veriflow_api.services.audit import record_audit_event
from veriflow_api.tasks.documents import process_document_task

router = APIRouter(prefix="/workspaces/{workspace_id}/documents")

WorkspaceReader = Annotated[
    WorkspaceMembership,
    Depends(require_workspace_roles(*list(WorkspaceRole))),
]
WorkspaceUploader = Annotated[
    WorkspaceMembership,
    Depends(
        require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER)
    ),
]


def enqueue_structured_ingestion(job_id: UUID) -> str:
    result = process_document_task.apply_async(
        args=[str(job_id)],
        queue=settings.celery_queue_name,
    )
    return str(result.id)


async def workspace_document(
    session: DatabaseSession,
    *,
    workspace_id: UUID,
    document_id: UUID,
) -> Document:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    workspace_id: UUID,
    document_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
    page_limit: Annotated[int, Query(ge=1, le=200)] = 100,
    section_limit: Annotated[int, Query(ge=1, le=200)] = 100,
    table_limit: Annotated[int, Query(ge=1, le=100)] = 50,
    table_row_limit: Annotated[int, Query(ge=0, le=500)] = 50,
) -> DocumentContentResponse:
    document = await workspace_document(
        session,
        workspace_id=workspace_id,
        document_id=document_id,
    )
    pages = (
        await session.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .limit(page_limit)
        )
    ).all()
    sections = (
        await session.scalars(
            select(DocumentSection)
            .where(DocumentSection.document_id == document_id)
            .order_by(DocumentSection.ordinal)
            .limit(section_limit)
        )
    ).all()
    tables = (
        await session.scalars(
            select(DocumentTable)
            .where(DocumentTable.document_id == document_id)
            .order_by(DocumentTable.ordinal)
            .limit(table_limit)
        )
    ).all()

    table_responses = [
        DocumentTableResponse(
            id=table.id,
            section_id=table.section_id,
            ordinal=table.ordinal,
            title=table.title,
            source_label=table.source_label,
            page_number=table.page_number,
            column_names=table.column_names,
            rows=table.rows[:table_row_limit],
            row_count=table.row_count,
            column_count=table.column_count,
            is_truncated=table.is_truncated or table.row_count > table_row_limit,
            table_metadata=table.table_metadata,
        )
        for table in tables
    ]
    return DocumentContentResponse(
        document=DocumentResponse.model_validate(document),
        pages=[DocumentPageResponse.model_validate(page) for page in pages],
        sections=[DocumentSectionResponse.model_validate(section) for section in sections],
        tables=table_responses,
        returned_page_count=len(pages),
        returned_section_count=len(sections),
        returned_table_count=len(tables),
        table_row_limit=table_row_limit,
    )


@router.post(
    "/{document_id}/ingest",
    response_model=DocumentResponse,
    dependencies=[Depends(validate_csrf)],
)
async def queue_structured_ingestion(
    workspace_id: UUID,
    document_id: UUID,
    _: WorkspaceUploader,
    context: AuthContextDependency,
    session: DatabaseSession,
) -> DocumentResponse:
    document = await workspace_document(
        session,
        workspace_id=workspace_id,
        document_id=document_id,
    )
    if not document.storage_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The document has no stored source object.",
        )

    active_job = await session.scalar(
        select(DocumentProcessingJob.id).where(
            DocumentProcessingJob.document_id == document_id,
            DocumentProcessingJob.status.in_(
                [
                    ProcessingJobStatus.QUEUED,
                    ProcessingJobStatus.PROCESSING,
                    ProcessingJobStatus.RETRYING,
                ]
            ),
        )
    )
    if active_job is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Structured ingestion is already active.",
        )

    job = DocumentProcessingJob(
        document_id=document.id,
        requested_by_id=context.user.id,
        job_type="structured_ingestion",
        status=ProcessingJobStatus.QUEUED,
        max_attempts=settings.processing_max_retries + 1,
        details={"manual_structured_ingestion": True},
    )
    session.add(job)
    document.status = DocumentStatus.QUEUED
    document.status_message = "Structured ingestion queued."
    document.processed_at = None
    record_audit_event(
        session,
        action="document.structured_ingestion.queued",
        resource_type="document",
        resource_id=str(document.id),
        actor_user_id=context.user.id,
        workspace_id=workspace_id,
        details={"job_id": str(job.id)},
    )
    await session.commit()

    try:
        job.celery_task_id = await run_in_threadpool(enqueue_structured_ingestion, job.id)
        await session.commit()
    except Exception as error:
        document.status = DocumentStatus.FAILED
        document.status_message = "The worker could not accept the structured-ingestion job."
        job.status = ProcessingJobStatus.FAILED
        job.last_error = str(error)[:4000]
        await session.commit()

    await session.refresh(document)
    return DocumentResponse.model_validate(document)
