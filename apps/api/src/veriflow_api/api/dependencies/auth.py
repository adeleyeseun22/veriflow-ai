import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veriflow_api.config import settings
from veriflow_api.database import get_db_session
from veriflow_api.models.user import User
from veriflow_api.models.workspace import WorkspaceMembership, WorkspaceRole
from veriflow_api.services.sessions import SessionData, read_session, revoke_session

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    session_token: str
    session_data: SessionData


async def get_auth_context(request: Request, session: DatabaseSession) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    session_data = await read_session(token)
    if session_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is missing or expired.",
        )

    user = await session.get(User, session_data.user_id)
    if user is None or not user.is_active:
        await revoke_session(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    return AuthContext(
        user=user,
        session_token=token,
        session_data=session_data,
    )


AuthContextDependency = Annotated[AuthContext, Depends(get_auth_context)]


async def validate_csrf(request: Request, context: AuthContextDependency) -> None:
    header_token = request.headers.get("x-csrf-token")
    cookie_token = request.cookies.get(settings.csrf_cookie_name)

    tokens_are_valid = (
        header_token is not None
        and cookie_token is not None
        and secrets.compare_digest(header_token, cookie_token)
        and secrets.compare_digest(header_token, context.session_data.csrf_token)
    )
    if not tokens_are_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed.",
        )


def require_workspace_roles(*allowed_roles: WorkspaceRole):
    async def dependency(
        workspace_id: UUID,
        context: AuthContextDependency,
        session: DatabaseSession,
    ) -> WorkspaceMembership:
        membership = await session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == context.user.id,
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )
        if allowed_roles and membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return membership

    return dependency
