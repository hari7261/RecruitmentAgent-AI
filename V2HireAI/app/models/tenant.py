"""
Tenant (Organization) ORM model.

Represents a client organization/institute that uses the platform.
Each tenant gets isolated workspaces, their own users, and data.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class Tenant(Base, SoftDeleteMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Branding ──────────────────────────────────────────────────────────────
    logo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="#2563eb")
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    # ── Settings ───────────────────────────────────────────────────────────────
    branding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User", back_populates="tenant", cascade="save-update, merge",
        passive_deletes=True,
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(  # type: ignore[name-defined]
        "Subscription", back_populates="tenant", cascade="all, delete-orphan"
    )
    openings: Mapped[list["Opening"]] = relationship(  # type: ignore[name-defined]
        "Opening", back_populates="tenant", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]
        "Application", back_populates="tenant", cascade="all, delete-orphan"
    )
    job_profiles: Mapped[list["JobProfile"]] = relationship(  # type: ignore[name-defined]
        "JobProfile", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} slug={self.slug!r}>"
