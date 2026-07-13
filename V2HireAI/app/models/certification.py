"""
Certification ORM model.
"""
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    candidate: Mapped["Candidate"] = relationship(  # type: ignore[name-defined]
        "Candidate", back_populates="certifications"
    )

    def __repr__(self) -> str:
        return f"<Certification name={self.name!r} issuer={self.issuer!r}>"
