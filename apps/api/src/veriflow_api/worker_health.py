from datetime import UTC, datetime

from redis import Redis

from veriflow_api.config import settings


def _client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def record_worker_heartbeat() -> None:
    client = _client()
    try:
        client.set(
            settings.worker_heartbeat_key,
            datetime.now(UTC).isoformat(),
            ex=settings.worker_heartbeat_ttl_seconds,
        )
    finally:
        client.close()


def worker_is_healthy_sync() -> bool:
    client = _client()
    try:
        return client.exists(settings.worker_heartbeat_key) == 1
    except Exception:
        return False
    finally:
        client.close()
