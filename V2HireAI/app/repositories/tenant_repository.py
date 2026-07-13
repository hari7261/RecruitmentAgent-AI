"""
Tenant repository — extends BaseRepository with tenant-specific queries.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tenant, session)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        result = await self._session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Tenant]:
        result = await self._session.execute(
            select(Tenant).where(Tenant.contact_email == email, Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_custom_domain(self, domain: str) -> Optional[Tenant]:
        result = await self._session.execute(
            select(Tenant).where(Tenant.custom_domain == domain, Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
