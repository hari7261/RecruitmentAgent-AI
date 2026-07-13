"""
Job Profile API endpoints — organization-scoped ATS scoring configuration.

POST /api/v1/profiles           → create job profile
GET  /api/v1/profiles           → list org profiles
GET  /api/v1/profiles/{id}      → profile detail
PUT  /api/v1/profiles/{id}      → update profile
DELETE /api/v1/profiles/{id}    → delete profile
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_session,
)
from app.core.auth import get_current_tenant, require_roles
from app.core.exceptions import ValidationError
from app.repositories.job_profile_repository import JobProfileRepository
from app.schemas.schemas import ErrorResponse, JobProfileCreate, JobProfileResponse, JobProfileUpdate
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/profiles", tags=["Job Profiles"])


@router.post(
    "",
    response_model=JobProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job profile for ATS scoring",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def create_profile(
    payload: JobProfileCreate,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> JobProfileResponse:
    repo = JobProfileRepository(session)
    from app.models.job_profile import JobProfile

    if payload.is_default:
        existing = await repo.get_default(current_tenant_id)
        if existing:
            existing.is_default = False
            await repo.update(existing)

    profile = JobProfile(tenant_id=current_tenant_id, **payload.model_dump())
    profile = await repo.create(profile)
    return JobProfileResponse.model_validate(profile)


@router.get(
    "",
    response_model=list[JobProfileResponse],
    summary="List all job profiles for current org",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_profiles(
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> list[JobProfileResponse]:
    repo = JobProfileRepository(session)
    profiles = await repo.get_all(tenant_id=current_tenant_id)
    return [JobProfileResponse.model_validate(p) for p in profiles]


@router.get(
    "/{profile_id}",
    response_model=JobProfileResponse,
    summary="Get single job profile detail",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> JobProfileResponse:
    repo = JobProfileRepository(session)
    profile = await repo.get(profile_id, tenant_id=current_tenant_id)
    if not profile:
        raise ValidationError(message="Profile not found", details={"profile_id": profile_id})
    return JobProfileResponse.model_validate(profile)


@router.put(
    "/{profile_id}",
    response_model=JobProfileResponse,
    summary="Update job profile",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def update_profile(
    profile_id: str,
    payload: JobProfileUpdate,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> JobProfileResponse:
    repo = JobProfileRepository(session)
    profile = await repo.get(profile_id, tenant_id=current_tenant_id)
    if not profile:
        raise ValidationError(message="Profile not found", details={"profile_id": profile_id})

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)

    if payload.is_default:
        existing = await repo.get_default(current_tenant_id)
        if existing and existing.id != profile.id:
            existing.is_default = False
            await repo.update(existing)

    profile = await repo.update(profile)
    return JobProfileResponse.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job profile",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def delete_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> None:
    repo = JobProfileRepository(session)
    profile = await repo.get(profile_id, tenant_id=current_tenant_id)
    if not profile:
        raise ValidationError(message="Profile not found", details={"profile_id": profile_id})
    await repo.soft_delete(profile_id, tenant_id=current_tenant_id)
    return None
