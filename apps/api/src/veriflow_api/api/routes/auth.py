from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from veriflow_api.api.dependencies.auth import (
    AuthContextDependency,
    DatabaseSession,
    validate_csrf,
)
from veriflow_api.config import settings
from veriflow_api.contracts.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from veriflow_api.models.user import User
from veriflow_api.security import hash_password, verify_password
from veriflow_api.services.audit import record_audit_event
from veriflow_api.services.sessions import create_session, revoke_session

router = APIRouter(prefix="/auth")


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    common = {
        "max_age": settings.session_ttl_seconds,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_samesite,
        "path": "/",
        "domain": settings.session_cookie_domain,
    }
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        **common,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: DatabaseSession,
) -> AuthResponse:
    normalized_email = payload.email.lower()
    existing_user = await session.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        full_name=payload.full_name,
        password_hash=await hash_password(payload.password),
    )
    session.add(user)

    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    record_audit_event(
        session,
        action="user.registered",
        resource_type="user",
        resource_id=str(user.id),
        actor_user_id=user.id,
    )
    await session.commit()
    await session.refresh(user)

    session_token, session_data = await create_session(user.id)
    set_auth_cookies(response, session_token, session_data.csrf_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        expires_in_seconds=settings.session_ttl_seconds,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession,
) -> AuthResponse:
    normalized_email = payload.email.lower()
    user = await session.scalar(select(User).where(User.email == normalized_email))

    if user is None or not await verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    record_audit_event(
        session,
        action="user.logged_in",
        resource_type="user",
        resource_id=str(user.id),
        actor_user_id=user.id,
    )
    await session.commit()

    session_token, session_data = await create_session(user.id)
    set_auth_cookies(response, session_token, session_data.csrf_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        expires_in_seconds=settings.session_ttl_seconds,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(validate_csrf)],
)
async def logout(
    response: Response,
    context: AuthContextDependency,
    session: DatabaseSession,
) -> MessageResponse:
    await revoke_session(context.session_token)
    clear_auth_cookies(response)

    record_audit_event(
        session,
        action="user.logged_out",
        resource_type="user",
        resource_id=str(context.user.id),
        actor_user_id=context.user.id,
    )

    return MessageResponse(message="Signed out successfully.")


@router.get("/me", response_model=UserResponse)
async def current_user(context: AuthContextDependency) -> UserResponse:
    return UserResponse.model_validate(context.user)
