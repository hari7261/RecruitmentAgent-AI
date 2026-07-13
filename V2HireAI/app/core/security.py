"""
Security utilities: JWT token creation/verification, password hashing.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Password Hashing ───────────────────────────────────────────────────────────
import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


# ── JWT Tokens ─────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The user ID (sub claim).
        expires_delta: Optional TTL override.
        extra_claims: Additional claims to embed (e.g. tenant_id, role).

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.debug("Created access token for user=%s", subject)
    return token


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a JWT refresh token with longer TTL."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.debug("Created refresh token for user=%s", subject)
    return token


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        JWTError: If token is invalid, expired, or has wrong claims.
    """
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    return payload


def decode_access_token(token: str) -> dict:
    """Decode an access token and validate type."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type: expected access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode a refresh token and validate type."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type: expected refresh token")
    return payload


def generate_api_key() -> str:
    """Generate a random API key string for organization-level access."""
    import secrets
    return secrets.token_urlsafe(32)


def _set_cookie_pair(
    response: Response,
    access_token: str,
    refresh_token: str,
    *,
    access_cookie_name: str,
    refresh_cookie_name: str,
) -> None:
    """Persist an auth token pair in HttpOnly cookies."""
    response.set_cookie(
        key=access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Persist primary employer/admin auth tokens in HttpOnly cookies."""
    _set_cookie_pair(
        response,
        access_token,
        refresh_token,
        access_cookie_name=settings.access_cookie_name,
        refresh_cookie_name=settings.refresh_cookie_name,
    )


def set_candidate_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Persist candidate-only auth tokens in separate HttpOnly cookies."""
    _set_cookie_pair(
        response,
        access_token,
        refresh_token,
        access_cookie_name=settings.candidate_access_cookie_name,
        refresh_cookie_name=settings.candidate_refresh_cookie_name,
    )


def _clear_cookie_pair(
    response: Response,
    *,
    access_cookie_name: str,
    refresh_cookie_name: str,
) -> None:
    """Remove an auth cookie pair from the client."""
    response.delete_cookie(
        key=access_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    response.delete_cookie(
        key=refresh_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove primary employer/admin auth cookies from the client."""
    _clear_cookie_pair(
        response,
        access_cookie_name=settings.access_cookie_name,
        refresh_cookie_name=settings.refresh_cookie_name,
    )


def clear_candidate_auth_cookies(response: Response) -> None:
    """Remove candidate-only auth cookies from the client."""
    _clear_cookie_pair(
        response,
        access_cookie_name=settings.candidate_access_cookie_name,
        refresh_cookie_name=settings.candidate_refresh_cookie_name,
    )
