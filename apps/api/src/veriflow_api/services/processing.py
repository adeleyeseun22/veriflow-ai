from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from veriflow_api.config import settings
from veriflow_api.database import async_session_factory
from veriflow_api.models.document import Document, DocumentStatus
from veriflow_api.models.processing_job import DocumentProcessingJob, ProcessingJobStatus
from veriflow_api.services.audit import record_audit_event
from veriflow_api.services.storage import ObjectStorageError, object_storage


class RecoverableProcessingError(RuntimeError):
    """A transient processing failure that may succeed when retried."""


class PermanentProcessingError(RuntimeError):
    """A processing failure that should not be retried."""


def calculate_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retry_delay_seconds(retry_number: int) -> int:
    return min(settings.processing_retry_base_seconds * (2 ** max(retry_number - 1, 0)), 60)


async def run_document_processing(job_id: UUID, celery_task_id: str | None) -> None:
    temporary_file = NamedTemporaryFile(prefix="veriflow-process-", delete=False)
    temporary_path = Path(temporary_file.name)
    temporary_file.close()

    try:
        async with async_session_factory() as session:
            job = await session.get(DocumentProcessingJob, job_id)
            if job is None:
                raise PermanentProcessingError("Processing job no longer exists.")
            document = await session.get(Document, job.document_id)
            if document is None:
                raise PermanentProcessingError("Document no longer exists.")
            if not document.storage_key:
                raise PermanentProcessingError("Document storage key is missing.")

            now = datetime.now(UTC)
            job.status = ProcessingJobStatus.PROCESSING
            job.celery_task_id = celery_task_id or job.celery_task_id
            job.attempts += 1
            job.started_at = now
            job.last_error = None
            document.status = DocumentStatus.PROCESSING
            document.status_message = "Verifying the stored file in the background."
            document.processing_attempts += 1
            await session.commit()

            try:
                await object_storage.download_file(
                    object_name=document.storage_key,
                    destination_path=temporary_path,
                )
            except ObjectStorageError as error:
                raise RecoverableProcessingError(str(error)) from error

            actual_size = temporary_path.stat().st_size
            actual_sha256 = await run_in_threadpool(calculate_file_sha256, temporary_path)
            if actual_size != document.size_bytes:
                raise PermanentProcessingError("Stored file size does not match upload metadata.")
            if actual_sha256 != document.sha256:
                raise PermanentProcessingError(
                    "Stored file checksum does not match upload metadata."
                )

            completed_at = datetime.now(UTC)
            metadata = dict(document.document_metadata)
            metadata["background_processing"] = {
                "integrity_verified": True,
                "verified_at": completed_at.isoformat(),
                "worker_task_id": celery_task_id,
            }
            document.document_metadata = metadata
            document.status = DocumentStatus.READY
            document.status_message = "Integrity verified. Ready for structured ingestion."
            document.processed_at = completed_at
            job.status = ProcessingJobStatus.SUCCEEDED
            job.completed_at = completed_at
            job.details = {
                **job.details,
                "verified_size_bytes": actual_size,
                "verified_sha256": actual_sha256,
            }
            record_audit_event(
                session,
                action="document.processing.completed",
                resource_type="document",
                resource_id=str(document.id),
                actor_user_id=job.requested_by_id,
                workspace_id=document.workspace_id,
                details={"job_id": str(job.id), "attempts": job.attempts},
            )
            await session.commit()
    finally:
        await run_in_threadpool(temporary_path.unlink, missing_ok=True)


async def mark_processing_retry(job_id: UUID, message: str) -> None:
    async with async_session_factory() as session:
        job = await session.get(DocumentProcessingJob, job_id)
        if job is None:
            return
        document = await session.get(Document, job.document_id)
        job.status = ProcessingJobStatus.RETRYING
        job.last_error = message[:4000]
        if document is not None:
            document.status = DocumentStatus.QUEUED
            document.status_message = "Temporary processing problem. A retry is scheduled."
        await session.commit()


async def mark_processing_failed(job_id: UUID, message: str) -> None:
    async with async_session_factory() as session:
        job = await session.get(DocumentProcessingJob, job_id)
        if job is None:
            return
        document = await session.get(Document, job.document_id)
        completed_at = datetime.now(UTC)
        job.status = ProcessingJobStatus.FAILED
        job.last_error = message[:4000]
        job.completed_at = completed_at
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.status_message = "Background processing failed. Retry is available."
            record_audit_event(
                session,
                action="document.processing.failed",
                resource_type="document",
                resource_id=str(document.id),
                actor_user_id=job.requested_by_id,
                workspace_id=document.workspace_id,
                details={"job_id": str(job.id), "error": message[:500]},
            )
        await session.commit()


async def active_job_for_document(document_id: UUID) -> DocumentProcessingJob | None:
    async with async_session_factory() as session:
        return await session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.document_id == document_id,
                DocumentProcessingJob.status.in_(
                    [
                        ProcessingJobStatus.QUEUED,
                        ProcessingJobStatus.PROCESSING,
                        ProcessingJobStatus.RETRYING,
                    ]
                ),
            )
            .order_by(DocumentProcessingJob.created_at.desc())
        )
