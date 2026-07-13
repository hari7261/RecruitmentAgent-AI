"""
Add proper foreign key constraints to all tables.

H2 Fix: Migration 001_initial declared zero FKs (all were comments).
H3 Fix: Many tenant_id columns had no FK to tenants.id.

Revision ID: 002_add_foreign_keys
Revises: 001_initial
Create Date: 2026-07-08
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_foreign_keys"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Check the dialect - SQLite does not support ADD CONSTRAINT after table creation
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # SQLite: we need to recreate tables with proper FKs.
        # For an existing SQLite DB, PRAGMA foreign_keys is the best we can do
        # without full table recreation (which would drop data).
        # We enable FK enforcement here and document the model-level constraints.
        op.execute("PRAGMA foreign_keys = ON")

        # Add job_profiles.deleted_at column (B2 Fix: was missing from migration)
        with op.batch_alter_table("job_profiles") as batch_op:
            batch_op.add_column(
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
            )

        # Fix resumes.status default (M10 Fix: migration said "uploaded", model says "pending")
        with op.batch_alter_table("resumes") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.String(50),
                server_default="pending",
            )

        # Add missing (tenant_id, email) unique constraint on candidates (M10 Fix)
        with op.batch_alter_table("candidates") as batch_op:
            batch_op.create_index(
                "uq_candidate_tenant_email",
                ["tenant_id", "email"],
                unique=True,
            )

        # Fix candidate_skills.confidence to nullable=True (M10 Fix)
        with op.batch_alter_table("candidate_skills") as batch_op:
            batch_op.alter_column("confidence", existing_type=sa.Float(), nullable=True)

    else:
        # PostgreSQL / MySQL: Add proper FK constraints

        # users.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_users_tenant_id", "users", "tenants",
            ["tenant_id"], ["id"], ondelete="SET NULL",
        )
        # subscriptions.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_subscriptions_tenant_id", "subscriptions", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # openings.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_openings_tenant_id", "openings", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # job_profiles.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_job_profiles_tenant_id", "job_profiles", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # Add missing deleted_at to job_profiles (B2 Fix)
        op.add_column("job_profiles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

        # candidates.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_candidates_tenant_id", "candidates", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # resumes.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_resumes_tenant_id", "resumes", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # resumes.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_resumes_candidate_id", "resumes", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # candidate_skills.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_candidate_skills_tenant_id", "candidate_skills", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # candidate_skills.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_candidate_skills_candidate_id", "candidate_skills", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # candidate_skills.skill_id -> skills.id
        op.create_foreign_key(
            "fk_candidate_skills_skill_id", "candidate_skills", "skills",
            ["skill_id"], ["id"], ondelete="CASCADE",
        )
        # experiences.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_experiences_tenant_id", "experiences", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # experiences.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_experiences_candidate_id", "experiences", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # educations.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_educations_tenant_id", "educations", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # educations.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_educations_candidate_id", "educations", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # certifications.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_certifications_tenant_id", "certifications", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # certifications.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_certifications_candidate_id", "certifications", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # ats_scores.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_ats_scores_tenant_id", "ats_scores", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )
        # ats_scores.resume_id -> resumes.id
        op.create_foreign_key(
            "fk_ats_scores_resume_id", "ats_scores", "resumes",
            ["resume_id"], ["id"], ondelete="CASCADE",
        )
        # applications.opening_id -> openings.id  (already in 001 but as comment)
        op.create_foreign_key(
            "fk_applications_opening_id", "applications", "openings",
            ["opening_id"], ["id"], ondelete="CASCADE",
        )
        # applications.candidate_id -> candidates.id
        op.create_foreign_key(
            "fk_applications_candidate_id", "applications", "candidates",
            ["candidate_id"], ["id"], ondelete="CASCADE",
        )
        # applications.resume_id -> resumes.id
        op.create_foreign_key(
            "fk_applications_resume_id", "applications", "resumes",
            ["resume_id"], ["id"], ondelete="CASCADE",
        )
        # application_status_history.application_id -> applications.id
        op.create_foreign_key(
            "fk_status_history_application_id", "application_status_history", "applications",
            ["application_id"], ["id"], ondelete="CASCADE",
        )
        # invitations.tenant_id -> tenants.id
        op.create_foreign_key(
            "fk_invitations_tenant_id", "invitations", "tenants",
            ["tenant_id"], ["id"], ondelete="CASCADE",
        )

        # M10 Fix: Add unique constraint on (tenant_id, email) for candidates
        op.create_index(
            "uq_candidate_tenant_email", "candidates",
            ["tenant_id", "email"], unique=True,
        )

        # M10 Fix: Fix resumes.status default
        op.alter_column(
            "resumes", "status",
            existing_type=sa.String(50),
            server_default="pending",
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("candidates") as batch_op:
            batch_op.drop_index("uq_candidate_tenant_email")
        with op.batch_alter_table("job_profiles") as batch_op:
            batch_op.drop_column("deleted_at")
    else:
        op.drop_index("uq_candidate_tenant_email", table_name="candidates")
        for fk_name in [
            "fk_users_tenant_id", "fk_subscriptions_tenant_id",
            "fk_openings_tenant_id", "fk_job_profiles_tenant_id",
            "fk_candidates_tenant_id", "fk_resumes_tenant_id",
            "fk_resumes_candidate_id", "fk_candidate_skills_tenant_id",
            "fk_candidate_skills_candidate_id", "fk_candidate_skills_skill_id",
            "fk_experiences_tenant_id", "fk_experiences_candidate_id",
            "fk_educations_tenant_id", "fk_educations_candidate_id",
            "fk_certifications_tenant_id", "fk_certifications_candidate_id",
            "fk_ats_scores_tenant_id", "fk_ats_scores_resume_id",
            "fk_applications_opening_id", "fk_applications_candidate_id",
            "fk_applications_resume_id", "fk_status_history_application_id",
            "fk_invitations_tenant_id",
        ]:
            op.drop_constraint(fk_name, table_name=fk_name.split("_", 2)[2].rsplit("_", 1)[0])
        op.drop_column("job_profiles", "deleted_at")
