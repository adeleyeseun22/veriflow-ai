import asyncio
from uuid import UUID

from celery import Task

from veriflow_api.config import settings
from veriflow_api.services.processing import (
    PermanentProcessingError,
    RecoverableProcessingError,
    mark_processing_failed,
    mark_processing_retry,
    retry_delay_seconds,
    run_document_processing,
)
from veriflow_api.worker import celery_app


@celery_app.task(bind=True, name="veriflow.process_document")
def process_document_task(task: Task, job_id: str) -> None:
    parsed_job_id = UUID(job_id)
    try:
        asyncio.run(run_document_processing(parsed_job_id, task.request.id))
    except RecoverableProcessingError as error:
        next_retry = task.request.retries + 1
        if next_retry > settings.processing_max_retries:
            asyncio.run(mark_processing_failed(parsed_job_id, str(error)))
            raise
        asyncio.run(mark_processing_retry(parsed_job_id, str(error)))
        raise task.retry(
            exc=error,
            countdown=retry_delay_seconds(next_retry),
            max_retries=settings.processing_max_retries,
        ) from error
    except PermanentProcessingError as error:
        asyncio.run(mark_processing_failed(parsed_job_id, str(error)))
        raise
    except Exception as error:
        asyncio.run(mark_processing_failed(parsed_job_id, str(error)))
        raise
