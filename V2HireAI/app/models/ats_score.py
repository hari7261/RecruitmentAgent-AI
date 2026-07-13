"""
ATSScore ORM model.

Stores the complete scoring breakdown for a resume.
One-to-one with Resume (via unique resume_id FK).
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class ATSScore(Base, SoftDeleteMixin):
    __tablename__ = "ats_scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Component Scores (each out of their max weight) ───────────────────────
    skill_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    certification_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    project_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Aggregates ────────────────────────────────────────────────────────────
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Reject"
    )  # Strong Hire | Hire | Review | Reject

    # ── Metadata ─────────────────────────────────────────────────────────────
    total_experience_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_skills_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_skills_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resume: Mapped["Resume"] = relationship(  # type: ignore[name-defined]
        "Resume", back_populates="ats_score"
    )

    def __repr__(self) -> str:
        return (
            f"<ATSScore resume={self.resume_id} total={self.total_score:.1f} "
            f"rec={self.recommendation!r}>"
        )
