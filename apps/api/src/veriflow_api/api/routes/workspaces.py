from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from veriflow_api.api.dependencies.auth import (
    AuthContextDependency,
    DatabaseSession,
    require_workspace_roles,
    validate_csrf,
)
from veriflow_api.contracts.workspace import (
    AuditLogResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)
from veriflow_api.models.audit_log import AuditLog
from veriflow_api.models.organization import Organization
from veriflow_api.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from veriflow_api.services.audit import record_audit_event
from veriflow_api.utils.slugs import unique_organization_slug, unique_workspace_slug

router = APIRouter(prefix="/workspaces")

WorkspaceMember = Annotated[
    WorkspaceMembership,
    Depends(
        require_workspace_roles(
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
            WorkspaceRole.REVIEWER,
        )
    ),
]
WorkspaceAdministrator = Annotated[
    WorkspaceMembership,
    Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(validate_csrf)],
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    context: AuthContextDependency,
    session: DatabaseSession,
) -> WorkspaceResponse:
    organization_name = " ".join(payload.organization_name.split())
    workspace_name = " ".join(payload.name.split())

    organization = Organization(
        name=organization_name,
        slug=await unique_organization_slug(session, organization_name),
        created_by_id=context.user.id,
    )
    session.add(organization)
    await session.flush()

    workspace = Workspace(
        organization_id=organization.id,
        name=workspace_name,
        slug=await unique_workspace_slug(session, organization.id, workspace_name),
        created_by_id=context.user.id,
    )
    session.add(workspace)
    await session.flush()

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=context.user.id,
        role=WorkspaceRole.OWNER,
    )
    session.add(membership)

    record_audit_event(
        session,
        action="workspace.created",
        resource_type="workspace",
        resource_id=str(workspace.id),
        workspace_id=workspace.id,
        actor_user_id=context.user.id,
        details={"organization_name": organization.name, "workspace_name": workspace.name},
    )
    await session.commit()
    await session.refresh(workspace)

    return WorkspaceResponse(
        id=workspace.id,
        organization_id=organization.id,
        organization_name=organization.name,
        name=workspace.name,
        slug=workspace.slug,
        role=membership.role,
        created_at=workspace.created_at,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    context: AuthContextDependency,
    session: DatabaseSession,
) -> list[WorkspaceResponse]:
    rows = (
        await session.execute(
            select(Workspace, Organization.name, WorkspaceMembership.role)
            .join(Organization, Organization.id == Workspace.organization_id)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(WorkspaceMembership.user_id == context.user.id)
            .order_by(Workspace.created_at.desc())
        )
    ).all()

    return [
        WorkspaceResponse(
            id=workspace.id,
            organization_id=workspace.organization_id,
            organization_name=organization_name,
            name=workspace.name,
            slug=workspace.slug,
            role=role,
            created_at=workspace.created_at,
        )
        for workspace, organization_name, role in rows
    ]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    membership: WorkspaceMember,
    session: DatabaseSession,
) -> WorkspaceResponse:
    row = (
        await session.execute(
            select(Workspace, Organization.name)
            .join(Organization, Organization.id == Workspace.organization_id)
            .where(Workspace.id == workspace_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    workspace, organization_name = row
    return WorkspaceResponse(
        id=workspace.id,
        organization_id=workspace.organization_id,
        organization_name=organization_name,
        name=workspace.name,
        slug=workspace.slug,
        role=membership.role,
        created_at=workspace.created_at,
    )


@router.get("/{workspace_id}/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    workspace_id: UUID,
    _: WorkspaceAdministrator,
    session: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AuditLogResponse]:
    audit_logs = (
        await session.scalars(
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            actor_user_id=log.actor_user_id,
            created_at=log.created_at,
        )
        for log in audit_logs
    ]
