"""
Tenant Service — orchestration for tenant (organization) management.

Provides business logic for platform admins and org users.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DuplicateResourceError, ValidationError
from app.models.tenant import Tenant
from app.models.subscription import Subscription, SubscriptionStatus, PlanType
from app.models.user import UserRole
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.utils.slug import generate_slug

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant (organization) operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TenantRepository(session)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return await self._repo.get_by_slug(slug)

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return await self._repo.get(tenant_id)

    async def create_tenant(
        self,
        name: str,
        slug: str,
        contact_email: str,
        **kwargs,
    ) -> Tenant:
        """Create a new tenant (organization) with default subscription."""
        existing = await self._repo.get_by_slug(slug)
        if existing:
            raise DuplicateResourceError(
                message=f"Tenant with slug '{slug}' already exists",
                details={"slug": slug},
            )

        tenant = Tenant(
            name=name,
            slug=slug,
            contact_email=contact_email,
            **kwargs,
        )
        tenant = await self._repo.create(tenant)

        # Create default subscription
        sub_repo = SubscriptionRepository(self._session)
        subscription = Subscription(
            tenant_id=tenant.id,
            plan=PlanType.FREE,
            status=SubscriptionStatus.TRIALING,
            resume_limit=settings.free_trial_resumes,
            user_limit=2,
            opening_limit=3,
            resumes_used_this_period=0,
        )
        await sub_repo.create(subscription)

        return tenant

    async def list_tenants(self, *, offset: int = 0, limit: int = 100) -> list[Tenant]:
        return list(await self._repo.get_all(offset=offset, limit=limit))

    async def update_tenant(self, tenant_id: str, **kwargs) -> Tenant:
        tenant = await self._repo.get(tenant_id)
        if not tenant:
            raise ValidationError(message="Tenant not found", details={"tenant_id": tenant_id})

        allowed_fields = {
            "name", "slug", "description", "contact_email", "contact_phone",
            "website", "logo_url", "primary_color", "custom_domain", "branding",
            "is_active",
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(tenant, key, value)

        # Regenerate slug if name changed
        if "name" in kwargs and "slug" not in kwargs:
            base_slug = generate_slug(kwargs["name"])
            tenant.slug = base_slug

        return await self._repo.update(tenant)
