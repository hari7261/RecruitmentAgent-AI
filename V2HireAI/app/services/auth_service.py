"""
Auth Service — handles authentication flow, token creation, user operations.
"""
import logging
from datetime import timedelta
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> User:
        """
        Verify email + password and return the user.
        Raises InvalidCredentialsError if not found or wrong password.
        """
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise InvalidCredentialsError(message="Invalid email or password")
        if not user.is_active:
            raise InactiveUserError(message="User account is inactive")
        if not user.hashed_password:
            raise InvalidCredentialsError(message="Password not set for this account")

        from app.core.security import verify_password
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError(message="Invalid email or password")

        return user

    async def create_user(
        self,
        email: str,
        password: str,
        role: str = "org_member",
        tenant_id: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> User:
        """Create a new user with hashed password."""
        from app.core.security import hash_password

        existing = await self._user_repo.get_by_email(email)
        if existing and not existing.deleted_at:
            raise ValueError(f"User with email {email} already exists")

        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role,
            tenant_id=tenant_id,
            full_name=full_name,
        )
        return await self._user_repo.create(user)

    async def create_tokens(self, user: User) -> dict:
        """Create access and refresh tokens for a user."""
        from app.core.security import (
            create_access_token,
            create_refresh_token,
        )

        extra_claims = {
            "tenant_id": user.tenant_id,
            "role": user.role,
        }

        access_expires = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_expires = timedelta(days=settings.refresh_token_expire_days)

        access = create_access_token(
            subject=user.id,
            expires_delta=access_expires,
            extra_claims=extra_claims,
        )
        refresh = create_refresh_token(
            subject=user.id,
            expires_delta=refresh_expires,
            extra_claims={"tenant_id": user.tenant_id},
        )

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    async def get_user_from_refresh_token(self, refresh_token: str) -> Optional[User]:
        """Validate refresh token and return the associated user."""
        try:
            from app.core.security import decode_refresh_token
            payload = decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
        except JWTError:
            return None

        if not user_id:
            return None

        user = await self._user_repo.get(user_id, allow_unscoped=True)
        if not user or not user.is_active:
            return None
        return user

    async def update_last_login(self, user: User) -> None:
        """Update the last_login_at timestamp."""
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)
        await self._user_repo.update(user)

    async def generate_api_key(self, user: User) -> str:
        """Generate and store an API key for the user."""
        from app.core.security import generate_api_key as gen_key
        key = gen_key()
        user.api_key = key
        from datetime import datetime, timezone
        user.api_key_created_at = datetime.now(timezone.utc)
        await self._user_repo.update(user)
        return key

    async def revoke_api_key(self, user: User) -> None:
        """Revoke the user's API key."""
        user.api_key = None
        user.api_key_created_at = None
        await self._user_repo.update(user)

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a random password reset token."""
        import secrets
        return secrets.token_urlsafe(32)
