"""
Public Portal API endpoints — no authentication required.

GET  /portal/list                        → list all active orgs
GET  /portal/o/{org_slug}                → org branding + active jobs
GET  /portal/o/{org_slug}/jobs           → list active openings
GET  /portal/o/{org_slug}/job/{slug}     → single job detail
GET  /portal/o/{org_slug}/dashboard      → candidate dashboard
GET  /portal/o/{org_slug}/apply/{slug}   → candidate applies (multipart)
"""
import logging
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session, get_public_service, get_application_service
from app.database.session import get_session_ctx
from app.core.exceptions import ValidationError
from app.core.security import hash_password, set_candidate_auth_cookies
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import (
    TenantResponse,
    OpeningResponse,
    ErrorResponse,
)
from app.models.user import User, UserRole
from app.services.public_service import PublicService
from app.services.application_service import ApplicationService
from app.services.auth_service import AuthService
from app.services.resume_service import ResumeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portal", tags=["Public Portal"])


@router.get(
    "/list",
    response_model=list[TenantResponse],
    summary="List all active organizations",
)
async def list_orgs() -> list[TenantResponse]:
    async with get_session_ctx() as session:
        repo = TenantRepository(session)
        tenants = await repo.get_all(limit=1000)
        active = [t for t in tenants if t.is_active and not t.deleted_at]
        return [TenantResponse.model_validate(t) for t in active]


@router.get(
    "/o/{org_slug}",
    summary="Public careers page for an organization",
)
async def get_org_portal(
    request: Request,
    org_slug: str,
    format: str | None = None,
    public_service: PublicService = Depends(get_public_service),
):
    if format == "json":
        tenant, openings = await public_service.get_public_openings(org_slug)
        return {
            "organization": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "logo_url": tenant.logo_url,
                "primary_color": tenant.primary_color,
                "website": tenant.website,
                "branding": tenant.branding or {},
            },
            "jobs": [OpeningResponse.model_validate(o) for o in openings],
        }

    if "text/html" in request.headers.get("accept", ""):
        return FileResponse("ui/portal/index.html")
    tenant, openings = await public_service.get_public_openings(org_slug)
    return {
        "organization": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "logo_url": tenant.logo_url,
            "primary_color": tenant.primary_color,
            "website": tenant.website,
            "branding": tenant.branding or {},
        },
        "jobs": [OpeningResponse.model_validate(o) for o in openings],
    }


@router.get(
    "/o/{org_slug}/apply/{opening_slug}",
    summary="Serve the apply HTML page to candidates",
)
async def get_apply_page(org_slug: str, opening_slug: str):
    return FileResponse("ui/portal/apply.html")


@router.post(
    "/o/{org_slug}/apply/{opening_slug}/preview",
    summary="Parse resume and prefill candidate details",
)
async def preview_apply_resume(
    org_slug: str,
    opening_slug: str,
    resume: UploadFile = File(...),
    public_service: PublicService = Depends(get_public_service),
) -> dict:
    await public_service.get_opening_detail(org_slug, opening_slug)

    async with get_session_ctx() as session:
        resume_service = ResumeService(session)
        preview = await resume_service.extract_contact_preview(resume)

    return {
        "message": "Resume parsed successfully",
        "candidate": {
            "full_name": preview["name"],
            "email": preview["email"],
            "phone": preview["phone"],
        },
        "parse_source": preview["parse_source"],
    }


@router.get(
    "/o/{org_slug}/candidate-login",
    summary="Serve the candidate login page",
)
async def get_candidate_login_page(org_slug: str):
    return FileResponse("ui/portal/candidate-login.html")


@router.get(
    "/o/{org_slug}/set-password",
    summary="Serve the candidate set-password page",
)
async def get_candidate_set_password_page(org_slug: str):
    return FileResponse("ui/portal/set-password.html")


@router.get(
    "/o/{org_slug}/my-applications",
    summary="Serve the my-applications HTML page to candidates",
)
async def get_my_applications_page(org_slug: str):
    return FileResponse("ui/portal/my-applications.html")


@router.get(
    "/o/{org_slug}/dashboard",
    summary="Serve the candidate dashboard HTML page",
)
async def get_client_dashboard(org_slug: str):
    return FileResponse("ui/portal/dashboard.html")


@router.get(
    "/o/{org_slug}/jobs",
    response_model=list[OpeningResponse],
    summary="List active job openings for an organization",
)
async def list_org_jobs(
    org_slug: str,
    public_service: PublicService = Depends(get_public_service),
) -> list[OpeningResponse]:
    tenant, openings = await public_service.get_public_openings(org_slug)
    return [OpeningResponse.model_validate(o) for o in openings]


@router.get(
    "/o/{org_slug}/job/{opening_slug}",
    response_model=OpeningResponse,
    summary="Single job opening detail",
)
async def get_job_detail(
    org_slug: str,
    opening_slug: str,
    public_service: PublicService = Depends(get_public_service),
) -> OpeningResponse:
    tenant, opening = await public_service.get_opening_detail(org_slug, opening_slug)
    return OpeningResponse.model_validate(opening)


@router.post(
    "/o/{org_slug}/apply/{opening_slug}",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a job opening (multipart form)",
)
async def apply_to_job(
    org_slug: str,
    opening_slug: str,
    resume: UploadFile = File(...),
    cover_letter: str | None = Form(default=None),
    source: str = Form(default="direct"),
    # H8 Fix: Accept candidate identity from form (don't silently discard)
    full_name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    public_service: PublicService = Depends(get_public_service),
    application_service: ApplicationService = Depends(get_application_service),
) -> dict:
    tenant, opening = await public_service.get_opening_detail(org_slug, opening_slug)

    application = await application_service.apply_to_opening(
        tenant_id=tenant.id,
        opening_id=opening.id,
        user_id=None,
        upload_file=resume,
        cover_letter=cover_letter,
        source=source,
        candidate_name=full_name,
        candidate_email=email,
        candidate_phone=phone,
    )
    response_payload = {
        "message": "Application submitted successfully",
        "application_id": application.id,
        "status": application.status,
        "total_score": application.total_score,
        "recommendation": application.recommendation,
        "candidate_portal_ready": False,
        "candidate_login_required": False,
        "candidate_set_password_required": False,
    }

    candidate_user = None
    normalized_email = email.lower().strip() if email else None
    if normalized_email:
        try:
            user_repo = UserRepository(application_service._session)
            existing_user = await user_repo.get_by_email(normalized_email)
            if existing_user and existing_user.role == UserRole.CANDIDATE:
                candidate_user = existing_user
                response_payload["candidate_portal_ready"] = True
                response_payload["candidate_login_required"] = True
            elif not existing_user:
                generated_password = secrets.token_urlsafe(24)
                candidate_user = await user_repo.create(
                    User(
                        email=normalized_email,
                        hashed_password=hash_password(generated_password),
                        full_name=full_name,
                        role=UserRole.CANDIDATE,
                        email_verified=False,
                    )
                )
                response_payload["candidate_portal_ready"] = True
                response_payload["candidate_login_required"] = False
                response_payload["candidate_set_password_required"] = True
        except Exception:
            logger.exception(
                "Candidate portal bootstrap failed after application submit for email=%s",
                normalized_email,
            )
    response = JSONResponse(content=response_payload, status_code=status.HTTP_201_CREATED)
    if normalized_email and candidate_user and not response_payload["candidate_login_required"]:
        try:
            auth_service = AuthService(application_service._session)
            tokens = await auth_service.create_tokens(candidate_user)
            set_candidate_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        except Exception:
            logger.exception(
                "Candidate cookie session setup failed after application submit for email=%s",
                normalized_email,
            )
    return response
