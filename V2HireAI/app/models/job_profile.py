"""
JobProfile ORM model.

Stores the ATS scoring configuration for a job opening or org-wide default.
Replaces file-based YAML configs with database-sourced profiles.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class JobProfile(Base, SoftDeleteMixin):
    __tablename__ = "job_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Tenant Link ────────────────────────────────────────────────────────────
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Optional Opening Association ──────────────────────────────────────────
    opening_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # ── Scoring Criteria ──────────────────────────────────────────────────────
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    min_experience_years: Mapped[float] = mapped_column(nullable=False, default=0.0)
    preferred_experience_years: Mapped[float] = mapped_column(nullable=False, default=5.0)
    preferred_education: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_certifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_certifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    min_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    preferred_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # ── Custom Weights ────────────────────────────────────────────────────────
    scoring_weights: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=dict
    )

    # ── Flags ─────────────────────────────────────────────────────────────────
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant", back_populates="job_profiles"
    )

    def __repr__(self) -> str:
        return (
            f"<JobProfile id={self.id} name={self.name!r} "
            f"tenant_id={self.tenant_id!r}>"
        )
