from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.models.audit_log import AuditLog


def record_audit_event(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    actor_user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        workspace_id=workspace_id,
        resource_id=resource_id,
        details=details or {},
    )
    session.add(audit_log)
    return audit_log
