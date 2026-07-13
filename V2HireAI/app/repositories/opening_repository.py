"""
Opening repository — tenant-scoped job posting queries.
"""
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opening import Opening
from app.repositories.base import BaseRepository


class OpeningRepository(BaseRepository[Opening]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Opening, session)

    async def get_by_slug(self, slug: str, tenant_id: str) -> Optional[Opening]:
        result = await self._session.execute(
            select(Opening).where(
                Opening.slug == slug,
                Opening.tenant_id == tenant_id,
                Opening.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_public(self, tenant_id: str) -> Sequence[Opening]:
        """List active, non-deleted openings for public portal."""
        result = await self._session.execute(
            select(Opening)
            .where(
                Opening.tenant_id == tenant_id,
                Opening.status == "active",
                Opening.deleted_at.is_(None),
            )
            .order_by(Opening.is_featured.desc(), Opening.sort_order.desc(), Opening.created_at.desc())
        )
        return result.scalars().all()

    async def get_with_counts(self, tenant_id: str) -> list[tuple[Opening, int]]:
        """List all openings with application counts."""
        from app.models.application import Application
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(Opening, func.count(Application.id).label("app_count"))
            .outerjoin(
                Application,
                (Application.opening_id == Opening.id)
                & (Application.deleted_at.is_(None)),
            )
            .where(
                Opening.tenant_id == tenant_id,
                Opening.deleted_at.is_(None),
            )
            .group_by(Opening.id)
            .order_by(Opening.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1] or 0) for row in result.all()]
