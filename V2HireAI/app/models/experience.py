"""
Experience ORM model.

Stores individual work history entries for a candidate, including
parsed dates and computed duration in months.
"""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    company: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Date Fields ───────────────────────────────────────────────────────────
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Raw date strings as found in resume (for audit/debug)
    raw_start_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_end_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    candidate: Mapped["Candidate"] = relationship(  # type: ignore[name-defined]
        "Candidate", back_populates="experiences"
    )

    def __repr__(self) -> str:
        return (
            f"<Experience company={self.company!r} title={self.job_title!r} "
            f"months={self.duration_months}>"
        )
