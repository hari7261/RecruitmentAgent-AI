"""
Candidate application tracking endpoint.

POST /api/v1/public/register           — public candidate registration
GET  /api/v1/public/my-applications    — list candidate applications (JWT)
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.database.session import get_session_ctx
from app.core.auth import get_current_candidate_user
from app.core.config import settings
from app.core.exceptions import DuplicateResourceError, ValidationError
from app.models.user import User, UserRole
from app.models.application import Application
from app.repositories.application_repository import ApplicationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import (
    CandidateApplicationSummary,
    CandidateSetPasswordRequest,
    CandidateRegisterRequest,
    ApplicationResponse,
    LoginRequest,
    UserResponse,
)
from app.core.security import (
    clear_candidate_auth_cookies,
    hash_password,
    set_candidate_auth_cookies,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Candidate"])


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Public candidate registration",
)
async def candidate_register(payload: CandidateRegisterRequest) -> dict:
    from app.core.security import create_access_token, create_refresh_token
    import secrets
    from datetime import datetime, timezone

    async with get_session_ctx() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(str(payload.email))
        if existing and not existing.deleted_at:
            raise DuplicateResourceError(message="Email already registered")

        verification_token = secrets.token_urlsafe(32)
        user = User(
            email=str(payload.email).lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.CANDIDATE,
            email_verified=False,
            email_verification_token=verification_token,
            email_verification_sent_at=datetime.now(timezone.utc),
        )
        user = await repo.create(user)
        tokens = await create_tokens_for_user(user, session)
    response = JSONResponse(content={
        "message": "Registration successful. Please verify your email.",
        "user_id": user.id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }, status_code=status.HTTP_201_CREATED)
    set_candidate_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post(
    "/login",
    response_model=dict,
    summary="Candidate portal login",
)
async def candidate_login(payload: LoginRequest) -> dict:
    from app.services.auth_service import AuthService

    async with get_session_ctx() as session:
        auth = AuthService(session)
        user = await auth.authenticate(str(payload.email), payload.password)
        if user.role != UserRole.CANDIDATE:
            raise HTTPException(status_code=403, detail="Candidate access required")
        await auth.update_last_login(user)
        tokens = await auth.create_tokens(user)

    response = JSONResponse(
        content={
            "message": "Candidate login successful",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        },
        status_code=status.HTTP_200_OK,
    )
    set_candidate_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current candidate session",
)
async def candidate_logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_candidate_auth_cookies(response)
    return response


async def create_tokens_for_user(user, session):
    from app.services.auth_service import AuthService
    auth = AuthService(session)
    return await auth.create_tokens(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current candidate profile",
)
async def candidate_me(
    current_user: User = Depends(get_current_candidate_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/set-password",
    response_model=dict,
    summary="Set password for current candidate session",
)
async def candidate_set_password(
    payload: CandidateSetPasswordRequest,
    current_user: User = Depends(get_current_candidate_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=403, detail="Candidate access required")

    current_user.hashed_password = hash_password(payload.new_password)
    await session.flush()
    return {"message": "Password set successfully"}


@router.get(
    "/my-applications",
    response_model=list[CandidateApplicationSummary],
    summary="List my applications (candidate)",
)
async def my_applications(
    current_user: User = Depends(get_current_candidate_user),
    session: AsyncSession = Depends(get_session),
) -> list[ApplicationResponse]:
    from app.models.candidate import Candidate
    # Fetch all Candidate IDs matching the user's email (M11 fix)
    candidate_result = await session.execute(
        select(Candidate.id).where(
            Candidate.email.ilike(current_user.email),
            Candidate.deleted_at.is_(None)
        )
    )
    candidate_ids = candidate_result.scalars().all()

    if not candidate_ids:
        return []

    repo = ApplicationRepository(session)
    rows = await repo.list_by_candidate_ids_with_details(list(candidate_ids))
    return [
        CandidateApplicationSummary(
            id=row["id"],
            tenant_id=row["tenant_id"],
            opening_id=row["opening_id"],
            opening_title=row.get("opening_title") or "Unknown",
            opening_slug=row.get("opening_slug") or "",
            candidate_id=row["candidate_id"],
            candidate_name=row.get("candidate_name"),
            candidate_email=row.get("candidate_email"),
            resume_id=row["resume_id"],
            status=row["status"],
            total_score=row.get("total_score"),
            recommendation=row.get("recommendation"),
            applied_at=row["applied_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh candidate portal token",
)
async def refresh_candidate_session(
    request: Request,
) -> dict:
    from app.services.auth_service import AuthService

    refresh_token = request.cookies.get(settings.candidate_refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing candidate refresh token")

    async with get_session_ctx() as session:
        auth = AuthService(session)
        user = await auth.get_user_from_refresh_token(refresh_token)
        if not user or user.role != UserRole.CANDIDATE:
            raise HTTPException(status_code=401, detail="Invalid or expired candidate refresh token")
        await auth.update_last_login(user)
        tokens = await auth.create_tokens(user)

    response = JSONResponse(content=tokens)
    set_candidate_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response
