"""
Pydantic v2 schemas for all API request/response models.
"""
from datetime import date, datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from urllib.parse import urlparse


def _normalize_logo_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return cleaned
    raise ValueError("Logo URL must be an absolute http(s) URL or root-relative path")


def _normalize_custom_domain(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    if "://" in cleaned:
        parsed = urlparse(cleaned)
        cleaned = parsed.netloc or parsed.path
    cleaned = cleaned.strip("/")
    if "." not in cleaned or any(ch.isspace() for ch in cleaned):
        raise ValueError("Custom domain must be a valid domain name")
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Role / Subscription constants (shared with models)
# ─────────────────────────────────────────────────────────────────────────────

class UserRole:
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    ORG_MEMBER = "org_member"
    CANDIDATE = "candidate"

    CHOICES = [SUPER_ADMIN, ORG_ADMIN, ORG_MEMBER, CANDIDATE]


# ─────────────────────────────────────────────────────────────────────────────
# Auth schemas
# ─────────────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    name: str
    slug: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    admin_email: EmailStr
    admin_password: str = Field(min_length=10, max_length=72)  # M9 Fix: Password policy
    admin_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=72)  # M9 Fix: Password policy


class CandidateSetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=10, max_length=72)


class CandidateRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)  # M9 Fix: Password policy
    full_name: Optional[str] = None


class CandidateApplicationRequest(BaseModel):
    cover_letter: Optional[str] = None
    source: str = "direct"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)  # M9 Fix: Password policy
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    tenant_id: Optional[str] = None
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "org_member"
    tenant_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# M8 Fix: Typed subscription update schema
class SubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    status: Optional[str] = None
    resume_limit: Optional[int] = Field(default=None, ge=0)
    user_limit: Optional[int] = Field(default=None, ge=0)
    opening_limit: Optional[int] = Field(default=None, ge=0)
    amount: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    next_billing_date: Optional[date] = None


# ─────────────────────────────────────────────────────────────────────────────
# Business value / eligibility schemas
# ─────────────────────────────────────────────────────────────────────────────

class PlanLimits(BaseModel):
    resume_limit: int
    user_limit: int
    opening_limit: int
    api_enabled: bool
    bulk_upload_enabled: bool
    custom_domain_enabled: bool


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    plan: str
    status: str
    limits: PlanLimits
    resumes_used_this_period: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    next_billing_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Tenant schemas
# ─────────────────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    branding: Optional[dict] = None

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_logo_url(value)

    @field_validator("custom_domain")
    @classmethod
    def validate_custom_domain(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_custom_domain(value)


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    branding: Optional[dict] = None
    is_active: Optional[bool] = None

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_logo_url(value)

    @field_validator("custom_domain")
    @classmethod
    def validate_custom_domain(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_custom_domain(value)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    branding: Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Opening schemas
# ─────────────────────────────────────────────────────────────────────────────

class OpeningCreate(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = "full-time"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "INR"
    is_featured: bool = False
    application_deadline: Optional[date] = None
    sort_order: int = 0
    meta: Optional[dict] = None
    profile: Optional["JobProfileCreate"] = None


class OpeningUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    application_deadline: Optional[date] = None
    sort_order: Optional[int] = None
    meta: Optional[dict] = None
    profile: Optional["JobProfileCreate"] = None


class OpeningStatusUpdate(BaseModel):
    status: str


class OpeningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    title: str
    slug: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    status: str
    is_featured: bool
    application_deadline: Optional[date] = None
    sort_order: int
    meta: Optional[dict] = None
    applications_count: int = 0
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Job Profile schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    opening_id: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float = 0.0
    preferred_experience_years: float = 5.0
    preferred_education: list[str] = Field(default_factory=list)
    required_certifications: list[str] = Field(default_factory=list)
    preferred_certifications: list[str] = Field(default_factory=list)
    min_projects: int = 1
    preferred_projects: int = 3
    scoring_weights: Optional[dict] = None
    is_default: bool = False
    is_active: bool = True


class JobProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    min_experience_years: Optional[float] = None
    preferred_experience_years: Optional[float] = None
    preferred_education: Optional[list[str]] = None
    required_certifications: Optional[list[str]] = None
    preferred_certifications: Optional[list[str]] = None
    min_projects: Optional[int] = None
    preferred_projects: Optional[int] = None
    scoring_weights: Optional[dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class JobProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    opening_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float
    preferred_experience_years: float
    preferred_education: list[str]
    required_certifications: list[str]
    preferred_certifications: list[str]
    min_projects: int
    preferred_projects: int
    scoring_weights: Optional[dict] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Application schemas
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    opening_id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    resume_id: str
    cover_letter: Optional[str] = None
    source: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    tags: Optional[list[str]] = None
    total_score: Optional[float] = None
    recommendation: Optional[str] = None
    applied_at: datetime
    updated_at: datetime
    status_changed_at: Optional[datetime] = None


class CandidateApplicationSummary(BaseModel):
    id: str
    tenant_id: str
    opening_id: str
    opening_title: str
    opening_slug: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    resume_id: str
    status: str
    total_score: Optional[float] = None
    recommendation: Optional[str] = None
    applied_at: datetime
    updated_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationNote(BaseModel):
    notes: str


class ApplicationTag(BaseModel):
    tag: str


# ─────────────────────────────────────────────────────────────────────────────
# Invitation schemas
# ─────────────────────────────────────────────────────────────────────────────

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "org_member"


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    role: str
    status: str
    invited_by_id: Optional[str] = None
    expires_at: datetime
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Platform / Admin schemas
# ─────────────────────────────────────────────────────────────────────────────

class PlatformHealthResponse(BaseModel):
    status: str
    total_tenants: int
    active_tenants: int
    total_users: int
    total_openings: int
    total_applications: int
    total_resumes_processed: int


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    total_subscriptions: dict[str, int]
    total_applications: int
    total_openings: int
    total_users: int
    monthly_recurring_revenue: float


# ─────────────────────────────────────────────────────────────────────────────
# Existing ATS schemas (kept for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

class SkillSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    normalized_name: str
    tenant_id: str


class ExperienceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    duration_months: Optional[int] = None
    raw_start_date: Optional[str] = None
    raw_end_date: Optional[str] = None
    description: Optional[str] = None


class EducationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    degree: Optional[str] = None
    degree_normalized: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None


class CertificationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    credential_id: Optional[str] = None


class CandidateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime


class SkillMatchDetails(BaseModel):
    matched_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    required_match_pct: float = 0.0
    preferred_match_pct: float = 0.0


class ATSScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    skill_score: float
    experience_score: float
    education_score: float
    certification_score: float
    project_score: float
    total_score: float
    recommendation: str
    total_experience_months: int
    matched_skills_count: int
    missing_skills_count: int
    scored_at: datetime


class ATSScoreDetailSchema(ATSScoreSchema):
    skill_details: Optional[SkillMatchDetails] = None
    experience_years: Optional[float] = None


class ResumeUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    candidate_id: str
    status: str
    message: str
    candidate: CandidateSchema
    ats_score: Optional[ATSScoreSchema] = None


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: str
    upload_time: datetime
    parse_source: Optional[str] = None
    candidate: Optional[CandidateSchema] = None
    ats_score: Optional[ATSScoreSchema] = None


class ResumeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    file_extension: str
    file_size_bytes: int
    status: str
    parse_source: Optional[str] = None
    upload_time: datetime
    parse_time_ms: Optional[float] = None
    extraction_time_ms: Optional[float] = None
    scoring_time_ms: Optional[float] = None

    candidate: Optional[CandidateSchema] = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[ExperienceSchema] = Field(default_factory=list)
    educations: list[EducationSchema] = Field(default_factory=list)
    certifications: list[CertificationSchema] = Field(default_factory=list)
    ats_score: Optional[ATSScoreDetailSchema] = None
    summary: Optional[str] = None


class ResumeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ResumeListItem]


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict[str, Any]] = None
