"""
Resume API endpoints.

All 5 endpoints:
  POST   /resume/upload       → upload, parse, and score a resume
  GET    /resume              → paginated list of resumes
  GET    /resume/{id}         → full resume detail
  GET    /resume/{id}/score   → ATS score + recommendation
  DELETE /resume/{id}         → delete resume and file
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_resume_service, get_ats_service
from app.core.auth import get_current_tenant, get_current_user, require_roles
from app.models.user import User
from app.schemas.schemas import (
    ATSScoreDetailSchema,
    ATSScoreSchema,
    ErrorResponse,
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeListItem,
    ResumeUploadResponse,
    CandidateSchema,
    ExperienceSchema,
    EducationSchema,
    CertificationSchema,
    SkillMatchDetails,
)
from app.services.resume_service import ResumeService
from app.services.ats_service import ATSService
from app.models.resume import Resume
from app.models.ats_score import ATSScore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["Resume"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /resume/upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a resume",
    description=(
        "Accepts a PDF or DOCX file. Validates, parses, extracts skills/experience/"
        "education/certifications, computes ATS score, and returns the full result."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        409: {"model": ErrorResponse, "description": "Duplicate resume"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Parse error"},
    },
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def upload_resume(
    file: Annotated[UploadFile, File(description="PDF or DOCX resume file")] = ...,
    job_profile: str = Query(default="default", description="Vacancy profile key"),
    service: ResumeService = Depends(get_resume_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ResumeUploadResponse:
    """Upload, parse, and score a resume file."""
    logger.info("Upload request: '%s' against profile '%s'", file.filename, job_profile)
    resume = await service.upload_and_process(file, job_profile, tenant_id=current_tenant_id)
    return _build_upload_response(resume)


# ─────────────────────────────────────────────────────────────────────────────
# GET /resume
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ResumeListResponse,
    summary="List all resumes",
    description="Paginated list of uploaded resumes with candidate info and ATS score summary.",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_resumes(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    service: ResumeService = Depends(get_resume_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ResumeListResponse:
    """Return a paginated list of resumes."""
    resumes, total = await service.list_resumes(page=page, page_size=page_size, tenant_id=current_tenant_id)
    items = [_build_list_item(r) for r in resumes]
    return ResumeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /resume/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Get resume details",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_resume(
    resume_id: str,
    job_profile: str = Query(default="default", description="Vacancy profile key"),
    service: ResumeService = Depends(get_resume_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ResumeDetailResponse:
    """Return full details for a specific resume including all extracted data."""
    resume = await service.get_resume(resume_id, tenant_id=current_tenant_id)
    return await _build_detail_response(resume, service, job_profile)


# ─────────────────────────────────────────────────────────────────────────────
# GET /resume/{resume_id}/score
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{resume_id}/score",
    response_model=ATSScoreDetailSchema,
    summary="Get ATS score",
    description="Returns the ATS score breakdown and hiring recommendation for a resume.",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_resume_score(
    resume_id: str,
    ats_service: ATSService = Depends(get_ats_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> ATSScoreDetailSchema:
    """Return the ATS score and recommendation for a resume."""
    score = await ats_service.get_score_by_resume_id(resume_id, tenant_id=current_tenant_id)
    return ATSScoreDetailSchema.model_validate(score)


# ─────────────────────────────────────────────────────────────────────────────
# GET /resume/job-profile/{profile_key}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/job-profile/{profile_key}",
    summary="Get job profile configuration details",
)
async def get_job_profile(profile_key: str) -> dict:
    """Load and return the job profile configuration details."""
    from app.scorer.ats_scorer import _load_job_profile
    profile = _load_job_profile(profile_key)
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /resume/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def delete_resume(
    resume_id: str,
    service: ResumeService = Depends(get_resume_service),
    current_tenant_id: str = Depends(get_current_tenant),
) -> None:
    """Delete a resume record and its uploaded file from disk."""
    await service.delete_resume(resume_id, tenant_id=current_tenant_id)


# ─────────────────────────────────────────────────────────────────────────────
# Response Builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_upload_response(resume: Resume) -> ResumeUploadResponse:
    return ResumeUploadResponse(
        resume_id=resume.id,
        candidate_id=resume.candidate_id,
        status=resume.status,
        message="Resume uploaded, parsed, and scored successfully.",
        candidate=CandidateSchema.model_validate(resume.candidate),
        ats_score=(
            ATSScoreSchema.model_validate(resume.ats_score)
            if resume.ats_score
            else None
        ),
    )


def _build_list_item(resume: Resume) -> ResumeListItem:
    return ResumeListItem(
        id=resume.id,
        original_filename=resume.original_filename,
        status=resume.status,
        upload_time=resume.upload_time,
        parse_source=resume.parse_source,
        candidate=(
            CandidateSchema.model_validate(resume.candidate)
            if resume.candidate
            else None
        ),
        ats_score=(
            ATSScoreSchema.model_validate(resume.ats_score)
            if resume.ats_score
            else None
        ),
    )


async def _build_detail_response(
    resume: Resume,
    service: ResumeService,
    job_profile: str = "default",
) -> ResumeDetailResponse:
    """Build the full detail response, loading child relations."""
    from sqlalchemy import select
    from app.models.skill import Skill, CandidateSkill
    from app.models.experience import Experience
    from app.models.education import Education
    from app.models.certification import Certification
    import json

    session = service._session

    # Load skills
    result = await session.execute(
        select(Skill)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == resume.candidate_id)
    )
    skills = result.scalars().all()

    # Load experiences
    exp_result = await session.execute(
        select(Experience).where(Experience.candidate_id == resume.candidate_id)
    )
    experiences = exp_result.scalars().all()

    # Load educations
    edu_result = await session.execute(
        select(Education).where(Education.candidate_id == resume.candidate_id)
    )
    educations = edu_result.scalars().all()

    # Load certifications
    cert_result = await session.execute(
        select(Certification).where(Certification.candidate_id == resume.candidate_id)
    )
    certifications = cert_result.scalars().all()

    # Parse stored summary
    summary = None
    if resume.parsed_json:
        try:
            parsed = json.loads(resume.parsed_json)
            summary = parsed.get("summary")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Build ATS detail schema
    ats_detail = None
    if resume.ats_score:
        # Load the job profile configuration to get required/preferred skills
        from app.scorer.ats_scorer import _load_job_profile
        from app.matcher.skill_matcher import match_skills
        
        profile = _load_job_profile(job_profile)
        required_skills = profile.get("required_skills", [])
        preferred_skills = profile.get("preferred_skills", [])
        
        skill_match = match_skills(
            extracted=[s.normalized_name for s in skills],
            required=required_skills,
            preferred=preferred_skills,
        )
        
        skill_details = SkillMatchDetails(
            matched_required=skill_match.matched_required,
            missing_required=skill_match.missing_required,
            matched_preferred=skill_match.matched_preferred,
            required_match_pct=skill_match.required_match_pct,
            preferred_match_pct=skill_match.preferred_match_pct,
        )

        ats_detail = ATSScoreDetailSchema(
            id=resume.ats_score.id,
            resume_id=resume.ats_score.resume_id,
            skill_score=resume.ats_score.skill_score,
            experience_score=resume.ats_score.experience_score,
            education_score=resume.ats_score.education_score,
            certification_score=resume.ats_score.certification_score,
            project_score=resume.ats_score.project_score,
            total_score=resume.ats_score.total_score,
            recommendation=resume.ats_score.recommendation,
            total_experience_months=resume.ats_score.total_experience_months,
            matched_skills_count=resume.ats_score.matched_skills_count,
            missing_skills_count=resume.ats_score.missing_skills_count,
            scored_at=resume.ats_score.scored_at,
            experience_years=round(resume.ats_score.total_experience_months / 12, 1),
            skill_details=skill_details,
        )

    return ResumeDetailResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        file_extension=resume.file_extension,
        file_size_bytes=resume.file_size_bytes,
        status=resume.status,
        parse_source=resume.parse_source,
        upload_time=resume.upload_time,
        parse_time_ms=resume.parse_time_ms,
        extraction_time_ms=resume.extraction_time_ms,
        scoring_time_ms=resume.scoring_time_ms,
        candidate=(
            CandidateSchema.model_validate(resume.candidate)
            if resume.candidate else None
        ),
        skills=[s.normalized_name for s in skills],
        experiences=[ExperienceSchema.model_validate(e) for e in experiences],
        educations=[EducationSchema.model_validate(e) for e in educations],
        certifications=[CertificationSchema.model_validate(c) for c in certifications],
        ats_score=ats_detail,
        summary=summary,
    )
