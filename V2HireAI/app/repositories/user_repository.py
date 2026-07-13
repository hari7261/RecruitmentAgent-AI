"""
User repository — extends BaseRepository with user-specific queries.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self, tenant_id: str, *, offset: int = 0, limit: int = 100
    ) -> Sequence[User]:
        result = await self._session.execute(
            select(User)
            .where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_by_tenant(self, tenant_id: str) -> int:
        return await self.count(tenant_id=tenant_id)

    async def get_by_api_key(self, api_key: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(
                User.api_key == api_key,
                User.is_active == True,  # noqa: E712
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
