import re
import secrets
import unicodedata
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.models.organization import Organization
from veriflow_api.models.workspace import Workspace

NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = NON_ALPHANUMERIC.sub("-", normalized.lower()).strip("-")
    return slug or "workspace"


async def unique_organization_slug(session: AsyncSession, name: str) -> str:
    base = slugify(name)
    candidate = base

    for _ in range(10):
        exists = await session.scalar(select(Organization.id).where(Organization.slug == candidate))
        if exists is None:
            return candidate
        candidate = f"{base}-{secrets.token_hex(3)}"

    return f"{base}-{secrets.token_hex(6)}"


async def unique_workspace_slug(
    session: AsyncSession,
    organization_id: UUID,
    name: str,
) -> str:
    base = slugify(name)
    candidate = base

    for _ in range(10):
        exists = await session.scalar(
            select(Workspace.id).where(
                Workspace.organization_id == organization_id,
                Workspace.slug == candidate,
            )
        )
        if exists is None:
            return candidate
        candidate = f"{base}-{secrets.token_hex(3)}"

    return f"{base}-{secrets.token_hex(6)}"
