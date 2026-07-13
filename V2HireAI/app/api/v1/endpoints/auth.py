"""
Authentication API endpoints.

POST /api/v1/auth/register   — create tenant + admin (superadmin only via admin panel)
POST /api/v1/auth/login      — email + password → JWT
POST /api/v1/auth/refresh    — rotate refresh token
GET  /api/v1/auth/me         — current user
POST /api/v1/auth/api-key    — generate API key
DELETE /api/v1/auth/api-key  — revoke API key
POST /api/v1/auth/password-reset — request password reset
POST /api/v1/auth/password-reset/confirm — reset password with token
"""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.database.session import get_session_ctx
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.exceptions import (
    DuplicateResourceError,
    InvalidCredentialsError,
    ValidationError,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    TokenResponse,
    UserResponse,
)
from app.core.security import clear_auth_cookies, set_auth_cookies

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization",
    description="Creates an organization and admin user. Intended for superadmin use.",
)
async def register_tenant(payload: RegisterRequest) -> dict:
    from app.services.auth_service import AuthService
    from app.services.tenant_service import TenantService

    async with get_session_ctx() as session:
        auth = AuthService(session)
        tenant_svc = TenantService(session)

        tenant = await tenant_svc.create_tenant(
            name=payload.name,
            slug=payload.slug,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            website=payload.website,
            description=payload.description,
        )

        admin = await auth.create_user(
            email=payload.admin_email,
            password=payload.admin_password,
            role=UserRole.ORG_ADMIN,
            tenant_id=tenant.id,
            full_name=payload.admin_name,
        )

        return {
            "message": "Organization created successfully",
            "tenant_id": tenant.id,
            "admin_user_id": admin.id,
            "access_url": "/api/v1/auth/login",
        }


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(payload: LoginRequest) -> TokenResponse:
    from app.services.auth_service import AuthService

    async with get_session_ctx() as session:
        auth = AuthService(session)
        user = await auth.authenticate(str(payload.email), payload.password)
        await auth.update_last_login(user)
        tokens = await auth.create_tokens(user)
    response = JSONResponse(content=TokenResponse(**tokens).model_dump())
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(
    request: Request,
    payload: RefreshRequest | None = None,
) -> TokenResponse:
    from app.services.auth_service import AuthService
    refresh_token = (
        payload.refresh_token
        if payload and payload.refresh_token
        else request.cookies.get(settings.refresh_cookie_name)
    )
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    async with get_session_ctx() as session:
        auth = AuthService(session)
        user = await auth.get_user_from_refresh_token(refresh_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        await auth.update_last_login(user)
        tokens = await auth.create_tokens(user)
    response = JSONResponse(content=TokenResponse(**tokens).model_dump())
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current user",
)
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post(
    "/password-reset",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request password reset",
)
async def request_password_reset(payload: PasswordResetRequest) -> dict:
    async with get_session_ctx() as session:
        result = await session.execute(
            select(User).where(User.email == str(payload.email).lower(), User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user and user.is_active:
            from app.services.auth_service import AuthService
            from datetime import datetime, timezone, timedelta
            reset_token = AuthService.generate_reset_token()
            user.reset_token = reset_token
            user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            await session.flush()
            logger.info("Password reset token generated for %s", payload.email)

    return {"message": "If an account exists, a password reset link has been sent."}


@router.post(
    "/password-reset/confirm",
    summary="Confirm password reset with token",
)
async def confirm_password_reset(payload: PasswordResetConfirm) -> dict:
    async with get_session_ctx() as session:
        result = await session.execute(
            select(User).where(User.reset_token == payload.token, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValidationError(message="Invalid or expired reset token")
        from datetime import datetime, timezone
        if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.now(timezone.utc):
            raise ValidationError(message="Reset token has expired")

        from app.core.security import hash_password
        user.hashed_password = hash_password(payload.new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        await session.flush()
        return {"message": "Password reset successful"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/api-key",
    response_model=dict,
    summary="Generate API key",
)
async def generate_api_key(current_user: User = Depends(get_current_user)) -> dict:
    from app.services.auth_service import AuthService

    async with get_session_ctx() as session:
        auth = AuthService(session)
        key = await auth.generate_api_key(current_user)

    return {"api_key": key}


@router.delete(
    "/api-key",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
)
async def revoke_api_key(current_user: User = Depends(get_current_user)) -> None:
    from app.services.auth_service import AuthService

    async with get_session_ctx() as session:
        auth = AuthService(session)
        await auth.revoke_api_key(current_user)
    return None
