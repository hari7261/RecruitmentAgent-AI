"""
JobProfile repository.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_profile import JobProfile
from app.repositories.base import BaseRepository


class JobProfileRepository(BaseRepository[JobProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(JobProfile, session)

    async def get_default(self, tenant_id: str) -> Optional[JobProfile]:
        result = await self._session.execute(
            select(JobProfile).where(
                JobProfile.tenant_id == tenant_id,
                JobProfile.is_default == True,  # noqa: E712
                JobProfile.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_opening(
        self, opening_id: str, tenant_id: str
    ) -> Optional[JobProfile]:
        result = await self._session.execute(
            select(JobProfile).where(
                JobProfile.opening_id == opening_id,
                JobProfile.tenant_id == tenant_id,
                JobProfile.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_tenant_defaults(self, tenant_id: str) -> Sequence[JobProfile]:
        result = await self._session.execute(
            select(JobProfile).where(
                JobProfile.tenant_id == tenant_id,
                JobProfile.opening_id.is_(None),
                JobProfile.deleted_at.is_(None),
            )
        )
        return result.scalars().all()
