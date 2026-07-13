"""
Subscription ORM model.

Tracks the plan, usage, and billing cycle for each tenant.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PlanType:
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    INSTITUTE = "institute"
    ENTERPRISE = "enterprise"

    CHOICES = [FREE, STARTER, GROWTH, INSTITUTE, ENTERPRISE]


class SubscriptionStatus:
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    SUSPENDED = "suspended"

    CHOICES = [ACTIVE, TRIALING, PAST_DUE, CANCELED, SUSPENDED]


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Tenant Link ────────────────────────────────────────────────────────────
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # ── Plan ──────────────────────────────────────────────────────────────────
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PlanType.FREE
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionStatus.TRIALING
    )

    # ── Limits ────────────────────────────────────────────────────────────────
    resume_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    user_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    opening_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    api_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    bulk_upload_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    custom_domain_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)

    # ── Usage ──────────────────────────────────────────────────────────────────
    resumes_used_this_period: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Billing ───────────────────────────────────────────────────────────────
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    billing_cycle: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # monthly/yearly
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    next_billing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant", back_populates="subscriptions"
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription id={self.id} tenant_id={self.tenant_id} "
            f"plan={self.plan!r} status={self.status!r}>"
        )
