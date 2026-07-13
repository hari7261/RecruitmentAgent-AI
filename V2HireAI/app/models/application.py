"""
Application ORM model.

Links a candidate's resume to a job opening with ATS score and
hiring pipeline status.
"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.candidate import Candidate as CandidateModel
    from app.models.resume import Resume as ResumeModel

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class ApplicationStatus:
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"
    HIRED = "hired"

    CHOICES = [APPLIED, SHORTLISTED, INTERVIEWING, OFFERED, REJECTED, HIRED]


class ApplicationSource:
    DIRECT = "direct"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    CAMPUS = "campus"
    JOB_PORTAL = "job_portal"
    OTHER = "other"

    CHOICES = [DIRECT, LINKEDIN, REFERRAL, CAMPUS, JOB_PORTAL, OTHER]


class Application(Base, SoftDeleteMixin):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Links ──────────────────────────────────────────────────────────────────
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opening_id: Mapped[str] = mapped_column(
        ForeignKey("openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ats_score_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # ── Application Data ──────────────────────────────────────────────────────
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=ApplicationSource.DIRECT
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ApplicationStatus.APPLIED
    )

    # ── Internal Notes ────────────────────────────────────────────────────────
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # ── Scoring Summary (denormalized for fast list queries) ──────────────────
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant", back_populates="applications"
    )
    opening: Mapped["Opening"] = relationship(  # type: ignore[name-defined]
        "Opening", back_populates="applications"
    )
    candidate: Mapped["CandidateModel"] = relationship(  # type: ignore[name-defined]
        "Candidate", lazy="joined"
    )
    resume: Mapped["ResumeModel"] = relationship(  # type: ignore[name-defined]
        "Resume", lazy="joined"
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(  # type: ignore[name-defined]
        "ApplicationStatusHistory", back_populates="application", cascade="all, delete-orphan"
    )

    # ── Hybrid properties for serialization (B4 fix) ──────────────────────────
    @hybrid_property
    def candidate_name(self) -> Optional[str]:
        return self.candidate.name if self.candidate else None

    @hybrid_property
    def candidate_email(self) -> Optional[str]:
        return self.candidate.email if self.candidate else None

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} candidate_id={self.candidate_id} "
            f"opening_id={self.opening_id} status={self.status!r}>"
        )
