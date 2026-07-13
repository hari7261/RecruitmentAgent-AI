"""
Resume ORM model.

Tracks each uploaded file, its parsing status, raw extracted text,
and the structured JSON output. A resume belongs to one Candidate.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin


class Resume(Base, SoftDeleteMixin):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── File Metadata ────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)

    # ── Parsing State ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | parsing | parsed | failed
    parse_source: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # docling | ocr
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timing ───────────────────────────────────────────────────────────────
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    parse_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraction_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scoring_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────────
    candidate: Mapped["Candidate"] = relationship(  # type: ignore[name-defined]
        "Candidate", back_populates="resumes"
    )
    ats_score: Mapped[Optional["ATSScore"]] = relationship(  # type: ignore[name-defined]
        "ATSScore", back_populates="resume", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} status={self.status!r} file={self.original_filename!r}>"
