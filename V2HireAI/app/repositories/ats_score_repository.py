"""
ATSScore repository — extends BaseRepository with score-specific queries.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ats_score import ATSScore
from app.repositories.base import BaseRepository


class ATSScoreRepository(BaseRepository[ATSScore]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ATSScore, session)

    async def get_by_resume_id(self, resume_id: str, tenant_id: Optional[str] = None) -> Optional[ATSScore]:
        stmt = select(ATSScore).where(ATSScore.resume_id == resume_id)
        if tenant_id:
            stmt = stmt.where(ATSScore.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
