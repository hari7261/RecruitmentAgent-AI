"""
Opening API endpoints — organization-scoped job posting CRUD.

POST /api/v1/openings       → create opening
GET  /api/v1/openings       → list org openings
GET  /api/v1/openings/{id}  → single opening detail
PATCH /api/v1/openings/{id}/status → open/close
DELETE /api/v1/openings/{id} → delete
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_opening_service,
    get_session,
)
from app.core.auth import get_current_tenant, require_roles
from app.core.exceptions import ValidationError
from app.schemas.schemas import (
    ErrorResponse,
    OpeningCreate,
    OpeningResponse,
    OpeningStatusUpdate,
)
from app.services.opening_service import OpeningService

router = APIRouter(prefix="/openings", tags=["Openings"])


@router.post(
    "",
    response_model=OpeningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job opening",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def create_opening(
    payload: OpeningCreate,
    opening_service: OpeningService = Depends(get_opening_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> OpeningResponse:
    tenant_id = current_tenant_id
    opening = await opening_service.create_opening(tenant_id, **payload.model_dump())
    return OpeningResponse.model_validate(opening)


@router.get(
    "",
    response_model=list[OpeningResponse],
    summary="List all openings for the current organization",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_openings(
    opening_service: OpeningService = Depends(get_opening_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> list[OpeningResponse]:
    openings = await opening_service.list_openings(current_tenant_id)
    return [OpeningResponse.model_validate(o) for o in openings]


@router.get(
    "/{opening_id}",
    response_model=OpeningResponse,
    summary="Get single opening detail",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_opening(
    opening_id: str,
    opening_service: OpeningService = Depends(get_opening_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> OpeningResponse:
    opening = await opening_service.get_opening(opening_id, current_tenant_id)
    if not opening:
        raise ValidationError(message="Opening not found", details={"opening_id": opening_id})
    return OpeningResponse.model_validate(opening)


@router.patch(
    "/{opening_id}/status",
    response_model=OpeningResponse,
    summary="Update opening status (active/paused/closed)",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def update_opening_status(
    opening_id: str,
    payload: OpeningStatusUpdate,
    opening_service: OpeningService = Depends(get_opening_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> OpeningResponse:
    opening = await opening_service.update_status(opening_id, current_tenant_id, payload.status)
    return OpeningResponse.model_validate(opening)


@router.delete(
    "/{opening_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an opening (soft delete)",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def delete_opening(
    opening_id: str,
    opening_service: OpeningService = Depends(get_opening_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> None:
    await opening_service.delete_opening(opening_id, current_tenant_id)
    return None
