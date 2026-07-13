"""
ATS Service — standalone service for ATS score retrieval.

Provides a clean interface for the GET /resume/{id}/score endpoint.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResumeNotFoundError
from app.models.ats_score import ATSScore
from app.repositories.ats_score_repository import ATSScoreRepository
from app.repositories.resume_repository import ResumeRepository

logger = logging.getLogger(__name__)


class ATSService:
    """Service for ATS score operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._score_repo = ATSScoreRepository(session)
        self._resume_repo = ResumeRepository(session)

    async def get_score_by_resume_id(self, resume_id: str, tenant_id: str = None) -> ATSScore:
        """
        Fetch the ATS score for a given resume.

        Raises:
            ResumeNotFoundError: if resume or score doesn't exist.
        """
        # Verify resume exists
        resume = await self._resume_repo.get(resume_id, tenant_id=tenant_id)
        if not resume:
            raise ResumeNotFoundError(
                message=f"Resume '{resume_id}' not found.",
                details={"resume_id": resume_id},
            )

        score = await self._score_repo.get_by_resume_id(resume_id, tenant_id=tenant_id)
        if not score:
            raise ResumeNotFoundError(
                message=f"ATS score for resume '{resume_id}' not found. "
                        "The resume may still be processing.",
                details={"resume_id": resume_id},
            )

        logger.debug("Retrieved ATS score for resume %s: %.1f", resume_id, score.total_score)
        return score
