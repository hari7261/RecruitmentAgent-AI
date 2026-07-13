"""
Application API endpoints — organization-scoped candidate management.

GET  /api/v1/applications/opening/{opening_id} → list applicants
GET  /api/v1/applications/{id}                → single application detail
PATCH /api/v1/applications/{id}/status        → move through pipeline
PATCH /api/v1/applications/{id}/note          → add internal note
DELETE /api/v1/applications/{id}/tag          → add/remove tag
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_application_service,
    get_session,
)
from app.core.auth import get_current_tenant, require_roles
from app.core.exceptions import ValidationError
from app.schemas.schemas import (
    ApplicationNote,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationTag,
    ErrorResponse,
)
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "/all",
    summary="List all applications with full candidate + score details",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_all_applications(
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> list[dict]:
    """
    Returns all applications for the org with candidate name/email,
    opening title, and full ATS score breakdown (skill gaps etc.).
    """
    from app.repositories.application_repository import ApplicationRepository
    repo = ApplicationRepository(session)
    rows = await repo.list_all_with_details(current_tenant_id)

    def _fmt(r: dict) -> dict:
        applied = r.get("applied_at")
        return {
            "id": r["id"],
            "opening_id": r["opening_id"],
            "opening_title": r.get("opening_title") or "Unknown",
            "opening_slug": r.get("opening_slug") or "",
            "candidate_id": r["candidate_id"],
            "candidate_name": r.get("candidate_name") or "Anonymous",
            "candidate_email": r.get("candidate_email") or "",
            "candidate_phone": r.get("candidate_phone") or "",
            "resume_id": r["resume_id"],
            "status": r["status"],
            "total_score": round(r["total_score"] or 0, 1),
            "recommendation": r.get("recommendation") or "N/A",
            "cover_letter": r.get("cover_letter") or "",
            "source": r.get("source") or "direct",
            "applied_at": applied.isoformat() if hasattr(applied, "isoformat") else str(applied),
            # ATS score breakdown
            "score_breakdown": {
                "skills": round(r.get("skill_score") or 0, 1),
                "experience": round(r.get("experience_score") or 0, 1),
                "education": round(r.get("education_score") or 0, 1),
                "certifications": round(r.get("certification_score") or 0, 1),
                "projects": round(r.get("project_score") or 0, 1),
            },
            "matched_skills_count": r.get("matched_skills_count") or 0,
            "missing_skills_count": r.get("missing_skills_count") or 0,
            "experience_months": r.get("total_experience_months") or 0,
        }

    return [_fmt(r) for r in rows]


@router.get(
    "/opening/{opening_id}",
    response_model=list[ApplicationResponse],
    summary="List applications for a job opening",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_applications(
    opening_id: str,
    app_service: ApplicationService = Depends(get_application_service),
    current_tenant_id: str = Depends(get_current_tenant),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> list[ApplicationResponse]:
    apps, total = await app_service.list_applications(
        opening_id, current_tenant_id, page=page, page_size=page_size
    )
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get single application detail",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_application(
    application_id: str,
    app_service: ApplicationService = Depends(get_application_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ApplicationResponse:
    app = await app_service.get_application(application_id, current_tenant_id)
    if not app:
        raise ValidationError(message="Application not found", details={"application_id": application_id})
    return ApplicationResponse.model_validate(app)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status in hiring pipeline",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    app_service: ApplicationService = Depends(get_application_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ApplicationResponse:
    app = await app_service.update_status(
        application_id, current_tenant_id, payload.status, notes=payload.notes
    )
    return ApplicationResponse.model_validate(app)


@router.patch(
    "/{application_id}/note",
    response_model=ApplicationResponse,
    summary="Add internal note to application",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def add_note(
    application_id: str,
    payload: ApplicationNote,
    app_service: ApplicationService = Depends(get_application_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ApplicationResponse:
    app = await app_service.add_note(application_id, current_tenant_id, payload.notes)
    return ApplicationResponse.model_validate(app)


@router.post(
    "/{application_id}/tag",
    response_model=ApplicationResponse,
    summary="Add tag to application",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def add_tag(
    application_id: str,
    payload: ApplicationTag,
    app_service: ApplicationService = Depends(get_application_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ApplicationResponse:
    app = await app_service.add_tag(application_id, current_tenant_id, payload.tag)
    return ApplicationResponse.model_validate(app)
