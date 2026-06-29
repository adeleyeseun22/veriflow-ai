import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from veriflow_api.cache import redis_client
from veriflow_api.config import settings

SESSION_PREFIX = "veriflow:session:"


@dataclass(frozen=True, slots=True)
class SessionData:
    user_id: UUID
    csrf_token: str
    issued_at: datetime


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_key(token: str) -> str:
    return f"{SESSION_PREFIX}{hash_session_token(token)}"


async def create_session(user_id: UUID) -> tuple[str, SessionData]:
    token = secrets.token_urlsafe(48)
    session_data = SessionData(
        user_id=user_id,
        csrf_token=secrets.token_urlsafe(32),
        issued_at=datetime.now(UTC),
    )
    payload = json.dumps(
        {
            "user_id": str(session_data.user_id),
            "csrf_token": session_data.csrf_token,
            "issued_at": session_data.issued_at.isoformat(),
        }
    )
    await redis_client.set(
        session_key(token),
        payload,
        ex=settings.session_ttl_seconds,
    )
    return token, session_data


async def read_session(token: str) -> SessionData | None:
    raw = await redis_client.get(session_key(token))
    if raw is None:
        return None

    try:
        payload = json.loads(raw)
        session_data = SessionData(
            user_id=UUID(payload["user_id"]),
            csrf_token=str(payload["csrf_token"]),
            issued_at=datetime.fromisoformat(payload["issued_at"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        await revoke_session(token)
        return None

    await redis_client.expire(session_key(token), settings.session_ttl_seconds)
    return session_data


async def revoke_session(token: str) -> None:
    await redis_client.delete(session_key(token))
