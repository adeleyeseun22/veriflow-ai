import asyncio
import os
from collections.abc import Coroutine
from typing import Any, TypeVar
from uuid import UUID

from celery import Task
from celery.signals import worker_process_shutdown

from veriflow_api.config import settings
from veriflow_api.database import engine
from veriflow_api.services.processing import (
    PermanentProcessingError,
    RecoverableProcessingError,
    mark_processing_failed,
    mark_processing_retry,
    retry_delay_seconds,
    run_document_processing,
)
from veriflow_api.worker import celery_app

ResultType = TypeVar("ResultType")

_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_pid: int | None = None


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """
    Return one persistent asyncio event loop for the current Celery
    worker process.

    Celery executes this task synchronously, while VeriFlow's database
    and processing services are asynchronous. Reusing one loop prevents
    asyncpg and SQLAlchemy connections from being attached to a loop
    that has already been closed by asyncio.run().
    """

    global _worker_loop
    global _worker_loop_pid

    current_pid = os.getpid()

    if _worker_loop is None or _worker_loop.is_closed() or _worker_loop_pid != current_pid:
        _worker_loop = asyncio.new_event_loop()
        _worker_loop_pid = current_pid
        asyncio.set_event_loop(_worker_loop)

    return _worker_loop


def run_async(
    coroutine: Coroutine[Any, Any, ResultType],
) -> ResultType:
    """Run an async operation on the worker's persistent event loop."""

    loop = get_worker_event_loop()
    return loop.run_until_complete(coroutine)


@worker_process_shutdown.connect
def close_worker_event_loop(**_: object) -> None:
    """Dispose async database connections before a worker exits."""

    global _worker_loop
    global _worker_loop_pid

    if _worker_loop is not None and not _worker_loop.is_closed():
        try:
            _worker_loop.run_until_complete(engine.dispose())
        finally:
            _worker_loop.close()

    _worker_loop = None
    _worker_loop_pid = None


@celery_app.task(bind=True, name="veriflow.process_document")
def process_document_task(task: Task, job_id: str) -> None:
    parsed_job_id = UUID(job_id)

    try:
        run_async(
            run_document_processing(
                parsed_job_id,
                task.request.id,
            )
        )
    except RecoverableProcessingError as error:
        next_retry = task.request.retries + 1

        if next_retry > settings.processing_max_retries:
            run_async(
                mark_processing_failed(
                    parsed_job_id,
                    str(error),
                )
            )
            raise

        run_async(
            mark_processing_retry(
                parsed_job_id,
                str(error),
            )
        )

        raise task.retry(
            exc=error,
            countdown=retry_delay_seconds(next_retry),
            max_retries=settings.processing_max_retries,
        ) from error
    except PermanentProcessingError as error:
        run_async(
            mark_processing_failed(
                parsed_job_id,
                str(error),
            )
        )
        raise
    except Exception as error:
        run_async(
            mark_processing_failed(
                parsed_job_id,
                str(error),
            )
        )
        raise
