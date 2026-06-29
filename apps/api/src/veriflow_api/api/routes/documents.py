from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from veriflow_api.api.dependencies.auth import (
    AuthContextDependency,
    DatabaseSession,
    require_workspace_roles,
    validate_csrf,
)
from veriflow_api.config import settings
from veriflow_api.contracts.document import (
    DocumentListResponse,
    DocumentResponse,
    DuplicateDocumentResponse,
)
from veriflow_api.models.document import Document, DocumentStatus
from veriflow_api.models.workspace import WorkspaceMembership, WorkspaceRole
from veriflow_api.services.audit import record_audit_event
from veriflow_api.services.documents import find_duplicate_document
from veriflow_api.services.storage import ObjectStorageError, object_storage
from veriflow_api.services.uploads import (
    UploadTooLargeError,
    UploadValidationError,
    stage_and_validate_upload,
)

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
WorkspaceUploader = Annotated[
    WorkspaceMembership,
    Depends(
        require_workspace_roles(
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
        )
    ),
]


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(validate_csrf)],
)
async def upload_document(
    workspace_id: UUID,
    _: WorkspaceUploader,
    context: AuthContextDependency,
    session: DatabaseSession,
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    try:
        staged = await stage_and_validate_upload(file)
    except UploadTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from error
    except UploadValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    document_id = uuid4()
    storage_key = f"workspaces/{workspace_id}/documents/{document_id}/{staged.original_filename}"
    stored = False

    try:
        duplicate = await find_duplicate_document(
            session,
            workspace_id=workspace_id,
            sha256=staged.sha256,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "This exact file already exists in the workspace.",
                    "document_id": str(duplicate.id),
                },
            )

        try:
            await object_storage.upload_file(
                source_path=staged.path,
                object_name=storage_key,
                content_type=staged.mime_type,
            )
            stored = True
        except ObjectStorageError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Object storage is temporarily unavailable.",
            ) from error

        document = Document(
            id=document_id,
            workspace_id=workspace_id,
            uploaded_by_id=context.user.id,
            display_name=staged.display_name,
            original_filename=staged.original_filename,
            file_extension=staged.extension,
            mime_type=staged.mime_type,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
            status=DocumentStatus.UPLOADED,
            status_message="Original file stored successfully.",
            storage_provider="minio",
            storage_bucket=settings.minio_bucket,
            storage_key=storage_key,
            document_metadata={
                "validated_format": staged.extension,
                "client_content_type": staged.client_content_type,
            },
        )
        session.add(document)
        record_audit_event(
            session,
            action="document.uploaded",
            resource_type="document",
            resource_id=str(document.id),
            actor_user_id=context.user.id,
            workspace_id=workspace_id,
            details={
                "filename": staged.original_filename,
                "size_bytes": staged.size_bytes,
                "sha256": staged.sha256,
            },
        )

        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            if stored:
                await object_storage.delete_object(storage_key)
            duplicate = await find_duplicate_document(
                session,
                workspace_id=workspace_id,
                sha256=staged.sha256,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "This exact file already exists in the workspace.",
                    "document_id": str(duplicate.id) if duplicate else None,
                },
            ) from error

        await session.refresh(document)
        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        if stored:
            try:
                await object_storage.delete_object(storage_key)
            except ObjectStorageError:
                pass
        raise
    finally:
        await staged.cleanup()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    workspace_id: UUID,
    _: WorkspaceReader,
    session: DatabaseSession,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
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
    sha256: Annotated[
        str,
        Query(
            min_length=64,
            max_length=64,
            pattern=r"^[0-9A-Fa-f]{64}$",
        ),
    ],
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
