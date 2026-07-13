"""
User ORM model.

Supports three roles:
  super_admin — platform owner (you)
  org_admin   — full org access
  org_member  — limited org access

Users may optionally belong to a tenant (org) for data isolation.
Super admins have tenant_id = NULL.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class UserRole:
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    ORG_MEMBER = "org_member"
    CANDIDATE = "candidate"

    CHOICES = [SUPER_ADMIN, ORG_ADMIN, ORG_MEMBER, CANDIDATE]


class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    tenant_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Auth ───────────────────────────────────────────────────────────────────
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UserRole.CANDIDATE
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)
    email_verification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── API Access ─────────────────────────────────────────────────────────────
    api_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    api_key_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant: Mapped[Optional["Tenant"]] = relationship(  # type: ignore[name-defined]
        "Tenant", back_populates="users"
    )
    invitations: Mapped[list["Invitation"]] = relationship(  # type: ignore[name-defined]
        "Invitation", back_populates="invited_by", cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} email={self.email!r} role={self.role!r} "
            f"tenant_id={self.tenant_id!r}>"
        )
