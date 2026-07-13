"""
Authentication and authorization dependencies for FastAPI.

Role hierarchy:
  super_admin → full platform access
  org_admin   → full org access
  org_member  → limited org access (read-mostly)
"""
import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.database.session import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not token:
        token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError(message="Token missing subject claim")
    except JWTError as exc:
        logger.warning("Invalid token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(session)
    user = await repo.get(user_id, allow_unscoped=True)
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise InactiveUserError(message="User account is inactive")

    return user


async def get_current_candidate_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get(settings.candidate_access_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Candidate not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError(message="Token missing subject claim")
    except JWTError as exc:
        logger.warning("Invalid candidate token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired candidate token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(session)
    user = await repo.get(user_id, allow_unscoped=True)
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Candidate user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise InactiveUserError(message="User account is inactive")
    if user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required",
        )
    return user


async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "super_admin":
        raise InsufficientPermissionsError(
            message="Super admin access required",
            details={"required_role": "super_admin", "current_role": current_user.role},
        )
    return current_user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
) -> str:
    """
    Return the tenant_id for the current authenticated user.

    Raises 403 if the user is a superadmin (no tenant context).
    Raises 401 if not authenticated.
    """
    if current_user.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin does not belong to a tenant. Use /admin endpoints directly.",
        )
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a tenant.",
        )
    return current_user.tenant_id


class RoleChecker:
    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise InsufficientPermissionsError(
                message="Insufficient permissions",
                details={
                    "required_roles": self.allowed_roles,
                    "current_role": current_user.role,
                },
            )
        return current_user


def require_roles(allowed_roles: list[str]) -> RoleChecker:
    return RoleChecker(allowed_roles)
