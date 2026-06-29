from celery import Celery
from celery.signals import heartbeat_sent, worker_ready

from veriflow_api.config import settings
from veriflow_api.worker_health import record_worker_heartbeat

celery_app = Celery(
    "veriflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["veriflow_api.tasks.documents"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    result_serializer="json",
    task_acks_late=True,
    task_default_queue=settings.celery_queue_name,
    task_reject_on_worker_lost=True,
    task_routes={
        "veriflow.process_document": {"queue": settings.celery_queue_name},
    },
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
    worker_prefetch_multiplier=1,
)


@worker_ready.connect
def on_worker_ready(**_: object) -> None:
    record_worker_heartbeat()


@heartbeat_sent.connect
def on_worker_heartbeat(**_: object) -> None:
    record_worker_heartbeat()
