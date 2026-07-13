"""
Public Service — handles unauthenticated public portal requests.

Provides data for candidates browsing job openings and org branding.
No auth required.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.opening import Opening
from app.models.tenant import Tenant
from app.repositories.opening_repository import OpeningRepository
from app.repositories.tenant_repository import TenantRepository

logger = logging.getLogger(__name__)


class PublicService:
    """Service for public (unauthenticated) API endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._opening_repo = OpeningRepository(session)
        self._tenant_repo = TenantRepository(session)

    async def get_public_openings(self, org_slug: str) -> tuple[Tenant, list[Opening]]:
        """Get all active openings for a public org portal."""
        tenant = await self._tenant_repo.get_by_slug(org_slug)
        if not tenant or not tenant.is_active:
            raise ValidationError(
                message="Organization not found or inactive",
                details={"org_slug": org_slug},
            )

        openings = await self._opening_repo.list_public(tenant.id)
        return tenant, list(openings)

    async def get_opening_detail(self, org_slug: str, opening_slug: str) -> tuple[Tenant, Opening]:
        """Get a single active opening for public view."""
        tenant = await self._tenant_repo.get_by_slug(org_slug)
        if not tenant or not tenant.is_active:
            raise ValidationError(
                message="Organization not found",
                details={"org_slug": org_slug},
            )

        opening = await self._opening_repo.get_by_slug(opening_slug, tenant.id)
        if not opening or opening.status != "active":
            raise ValidationError(
                message="Job opening not found or not active",
                details={"opening_slug": opening_slug},
            )

        return tenant, opening

    async def get_org_branding(self, org_slug: str) -> Tenant:
        """Get tenant branding for public portal."""
        tenant = await self._tenant_repo.get_by_slug(org_slug)
        if not tenant or not tenant.is_active:
            raise ValidationError(message="Organization not found", details={"org_slug": org_slug})
        return tenant
