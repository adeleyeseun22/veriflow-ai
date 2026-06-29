from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from veriflow_api.models.workspace import WorkspaceRole


class WorkspaceCreateRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    name: str = Field(min_length=2, max_length=160)


class WorkspaceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    name: str
    slug: str
    role: WorkspaceRole
    created_at: datetime


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    actor_user_id: UUID | None
    created_at: datetime
