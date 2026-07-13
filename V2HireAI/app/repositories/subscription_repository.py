"""
Subscription repository — tenant-scoped subscription tracking.
"""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subscription, session)

    async def get_by_tenant(self, tenant_id: str) -> Optional[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def increment_resumes_used(self, subscription_id: str, count: int = 1) -> Optional[Subscription]:
        """Atomically increment the resumes_used counter."""
        from sqlalchemy import update
        stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(resumes_used_this_period=Subscription.resumes_used_this_period + count)
            .returning(Subscription)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()
