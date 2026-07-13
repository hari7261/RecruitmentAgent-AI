"""
Opening (Job Posting) ORM model.

Created by organizations to post job openings.
Published openings appear on the public careers portal.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin
from app.utils.slug import generate_slug


class OpeningStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"

    CHOICES = [DRAFT, ACTIVE, PAUSED, CLOSED, ARCHIVED]


class EmploymentType:
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    REMOTE = "remote"


class Opening(Base, SoftDeleteMixin):
    __tablename__ = "openings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Tenant Link ────────────────────────────────────────────────────────────
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Core Content ──────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Metadata ───────────────────────────────────────────────────────────────
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=EmploymentType.FULL_TIME
    )
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="INR")

    # ── Status & Visibility ───────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OpeningStatus.DRAFT
    )
    is_featured: Mapped[bool] = mapped_column(nullable=False, default=False)
    application_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Custom Fields ──────────────────────────────────────────────────────────
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant", back_populates="openings"
    )
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]
        "Application", back_populates="opening", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Opening id={self.id} title={self.title!r} "
            f"status={self.status!r} tenant_id={self.tenant_id!r}>"
        )
