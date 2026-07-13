"""
Education ORM model.

Stores degree entries with both raw and normalized degree names.
"""
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Education(Base):
    __tablename__ = "educations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    degree: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    degree_normalized: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    institution: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    candidate: Mapped["Candidate"] = relationship(  # type: ignore[name-defined]
        "Candidate", back_populates="educations"
    )

    def __repr__(self) -> str:
        return (
            f"<Education degree={self.degree_normalized!r} "
            f"institution={self.institution!r} year={self.graduation_year}>"
        )
