"""
Initial migration — create all tables for the multi-tenant recruitment platform.

Revision ID: 001_initial
Revises: 
Create Date: 2025-07-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ── revision identifiers ────────────────────────────────────────────────────────
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── tenants ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(1000), nullable=True),
        sa.Column("primary_color", sa.String(20), nullable=True, server_default="#2563eb"),
        sa.Column("custom_domain", sa.String(255), nullable=True, unique=True),
        sa.Column("branding", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_contact_email", "tenants", ["contact_email"])
    op.create_index("ix_tenants_custom_domain", "tenants", ["custom_domain"])

    # ── users ───────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verification_token", sa.String(128), nullable=True, unique=True),
        sa.Column("email_verification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_token", sa.String(128), nullable=True, unique=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_key", sa.String(64), nullable=True, unique=True),
        sa.Column("api_key_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── subscriptions ───────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(50), nullable=False, server_default="trialing"),
        sa.Column("resume_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("user_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("opening_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("api_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("bulk_upload_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("custom_domain_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("resumes_used_this_period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("billing_cycle", sa.String(20), nullable=True),
        sa.Column("payment_method", sa.String(100), nullable=True),
        sa.Column("next_billing_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    # FK: subscriptions.tenant_id -> tenants.id (enforced at app level for SQLite)

    # ── openings ────────────────────────────────────────────────────────────────
    op.create_table(
        "openings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("employment_type", sa.String(50), nullable=True, server_default="full-time"),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_openings_tenant_id", "openings", ["tenant_id"])
    op.create_index("ix_openings_slug", "openings", ["slug"])
    op.create_index("ix_openings_status", "openings", ["status"])
    # FK: openings.tenant_id -> tenants.id

    # ── job_profiles ────────────────────────────────────────────────────────────
    op.create_table(
        "job_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("opening_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("min_experience_years", sa.Float(), nullable=False, server_default="0"),
        sa.Column("preferred_experience_years", sa.Float(), nullable=False, server_default="5"),
        sa.Column("preferred_education", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("required_certifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_certifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("min_projects", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("preferred_projects", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scoring_weights", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_job_profiles_tenant_id", "job_profiles", ["tenant_id"])
    op.create_index("ix_job_profiles_opening_id", "job_profiles", ["opening_id"])
    # FK: job_profiles.tenant_id -> tenants.id

    # ── candidates ──────────────────────────────────────────────────────────────
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])
    # FK: candidates.tenant_id -> tenants.id

    # ── resumes ─────────────────────────────────────────────────────────────────
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_extension", sa.String(10), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("parse_source", sa.String(50), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.Text(), nullable=True),
        sa.Column("parse_time_ms", sa.Float(), nullable=True),
        sa.Column("extraction_time_ms", sa.Float(), nullable=True),
        sa.Column("scoring_time_ms", sa.Float(), nullable=True),
        sa.Column("upload_time", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_resumes_tenant_id", "resumes", ["tenant_id"])
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])
    op.create_index("ix_resumes_file_hash", "resumes", ["file_hash"])
    # FK: resumes.candidate_id -> candidates.id

    # ── skills ──────────────────────────────────────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("normalized_name", sa.String(255), nullable=False, unique=True),
        sa.Column("category", sa.String(100), nullable=True),
    )
    op.create_index("ix_skills_normalized", "skills", ["normalized_name"], unique=True)

    # ── candidate_skills ────────────────────────────────────────────────────────
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="resume"),
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_candidate_skills_tenant_id", "candidate_skills", ["tenant_id"])
    # unique constraint added inline in model for SQLite compatibility
    # FK: candidate_skills.candidate_id -> candidates.id
    # FK: candidate_skills.skill_id -> skills.id

    # ── experiences ─────────────────────────────────────────────────────────────
    op.create_table(
        "experiences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("raw_start_date", sa.String(100), nullable=True),
        sa.Column("raw_end_date", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_experiences_tenant_id", "experiences", ["tenant_id"])
    # FK: experiences.candidate_id -> candidates.id

    # ── educations ──────────────────────────────────────────────────────────────
    op.create_table(
        "educations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("degree", sa.String(255), nullable=True),
        sa.Column("degree_normalized", sa.String(255), nullable=True),
        sa.Column("institution", sa.String(255), nullable=True),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("gpa", sa.String(50), nullable=True),
    )
    op.create_index("ix_educations_tenant_id", "educations", ["tenant_id"])
    # FK: educations.candidate_id -> candidates.id

    # ── certifications ──────────────────────────────────────────────────────────
    op.create_table(
        "certifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("credential_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_certifications_tenant_id", "certifications", ["tenant_id"])
    # FK: certifications.candidate_id -> candidates.id

    # ── ats_scores ──────────────────────────────────────────────────────────────
    op.create_table(
        "ats_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("resume_id", sa.String(36), nullable=False),
        sa.Column("skill_score", sa.Float(), nullable=False),
        sa.Column("experience_score", sa.Float(), nullable=False),
        sa.Column("education_score", sa.Float(), nullable=False),
        sa.Column("certification_score", sa.Float(), nullable=False),
        sa.Column("project_score", sa.Float(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(50), nullable=False),
        sa.Column("total_experience_months", sa.Integer(), nullable=False),
        sa.Column("matched_skills_count", sa.Integer(), nullable=False),
        sa.Column("missing_skills_count", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ats_scores_tenant_id", "ats_scores", ["tenant_id"])
    op.create_index("ix_ats_scores_resume_id", "ats_scores", ["resume_id"])
    # FK: ats_scores.resume_id -> resumes.id

    # ── applications ────────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("opening_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("resume_id", sa.String(36), nullable=False),
        sa.Column("ats_score_id", sa.String(36), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True, server_default="direct"),
        sa.Column("status", sa.String(50), nullable=False, server_default="applied"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(50), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_applications_tenant_id", "applications", ["tenant_id"])
    op.create_index("ix_applications_opening_id", "applications", ["opening_id"])
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])
    op.create_index("ix_applications_resume_id", "applications", ["resume_id"])
    op.create_index("ix_applications_total_score", "applications", ["total_score"])
    # FK: applications.opening_id -> openings.id
    # FK: applications.candidate_id -> candidates.id
    # FK: applications.resume_id -> resumes.id

    # ── application_status_history ──────────────────────────────────────────────
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("from_status", sa.String(50), nullable=True),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_status_history_app_id", "application_status_history", ["application_id"])
    # FK: application_status_history.application_id -> applications.id

    # ── invitations ─────────────────────────────────────────────────────────────
    op.create_table(
        "invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="org_member"),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("invited_by_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invitations_tenant_id", "invitations", ["tenant_id"])
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("invitations")
    op.drop_table("application_status_history")
    op.drop_table("applications")
    op.drop_table("ats_scores")
    op.drop_table("certifications")
    op.drop_table("educations")
    op.drop_table("experiences")
    op.drop_table("candidate_skills")
    op.drop_table("skills")
    op.drop_table("resumes")
    op.drop_table("candidates")
    op.drop_table("job_profiles")
    op.drop_table("openings")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("tenants")
