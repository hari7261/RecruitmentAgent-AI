"""
Resume repository — extends BaseRepository with resume-specific queries.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import Resume
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Resume, session)

    async def get_by_hash(self, file_hash: str, tenant_id: str) -> Optional[Resume]:
        result = await self._session.execute(
            select(Resume).where(
                Resume.file_hash == file_hash,
                Resume.tenant_id == tenant_id,
                Resume.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, resume_id: str, tenant_id: Optional[str] = None) -> Optional[Resume]:
        stmt = select(Resume).options(
            selectinload(Resume.candidate),
            selectinload(Resume.ats_score),
        )
        if tenant_id:
            stmt = stmt.where(Resume.tenant_id == tenant_id)
        stmt = stmt.where(Resume.id == resume_id, Resume.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_relations(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        tenant_id: Optional[str] = None,
    ) -> Sequence[Resume]:
        stmt = select(Resume).options(
            selectinload(Resume.candidate),
            selectinload(Resume.ats_score),
        ).order_by(Resume.upload_time.desc())
        if tenant_id:
            stmt = stmt.where(Resume.tenant_id == tenant_id)
        stmt = stmt.where(Resume.deleted_at.is_(None)).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        resume_id: str,
        status: str,
        error_message: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[Resume]:
        resume = await self.get(resume_id, tenant_id)
        if resume:
            resume.status = status
            if error_message is not None:
                resume.error_message = error_message
            await self._session.flush()
        return resume
