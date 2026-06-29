import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.models.document import Document

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def normalize_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters.")
    return normalized


async def find_duplicate_document(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    sha256: str,
) -> Document | None:
    normalized_sha256 = normalize_sha256(sha256)
    return await session.scalar(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.sha256 == normalized_sha256,
        )
    )
