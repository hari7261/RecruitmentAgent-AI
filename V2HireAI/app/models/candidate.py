"""
Candidate ORM model.

Represents a unique individual. A candidate may have multiple
resume submissions (tracked via the Resume model).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class Candidate(Base, SoftDeleteMixin):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────────────────────────────────
    resumes: Mapped[list["Resume"]] = relationship(  # type: ignore[name-defined]
        "Resume", back_populates="candidate", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["Experience"]] = relationship(  # type: ignore[name-defined]
        "Experience", back_populates="candidate", cascade="all, delete-orphan"
    )
    educations: Mapped[list["Education"]] = relationship(  # type: ignore[name-defined]
        "Education", back_populates="candidate", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(  # type: ignore[name-defined]
        "Certification", back_populates="candidate", cascade="all, delete-orphan"
    )
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(  # type: ignore[name-defined]
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} name={self.name!r} email={self.email!r}>"
