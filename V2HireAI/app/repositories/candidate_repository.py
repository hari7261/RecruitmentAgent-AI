"""
Candidate repository — extends BaseRepository with candidate-specific queries.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.repositories.base import BaseRepository


class CandidateRepository(BaseRepository[Candidate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Candidate, session)

    async def get_by_email(self, email: str, tenant_id: Optional[str] = None) -> Optional[Candidate]:
        stmt = select(Candidate).where(Candidate.email.ilike(email))
        if tenant_id:
            stmt = stmt.where(Candidate.tenant_id == tenant_id)
        stmt = stmt.where(Candidate.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_all_relations(self, candidate_id: str, tenant_id: Optional[str] = None) -> Optional[Candidate]:
        stmt = select(Candidate).options(
            selectinload(Candidate.resumes),
            selectinload(Candidate.experiences),
            selectinload(Candidate.educations),
            selectinload(Candidate.certifications),
            selectinload(Candidate.candidate_skills),
        )
        if tenant_id:
            stmt = stmt.where(Candidate.tenant_id == tenant_id)
        stmt = stmt.where(Candidate.id == candidate_id, Candidate.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
