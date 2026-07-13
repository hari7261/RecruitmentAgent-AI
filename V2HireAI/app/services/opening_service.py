"""
Opening Service — orchestration for job posting CRUD + publishing.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.utils.slug import generate_slug
from app.models.opening import Opening
from app.models.job_profile import JobProfile
from app.repositories.opening_repository import OpeningRepository
from app.repositories.job_profile_repository import JobProfileRepository

logger = logging.getLogger(__name__)


class OpeningService:
    """Service for job opening operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OpeningRepository(session)
        self._profile_repo = JobProfileRepository(session)

    async def create_opening(self, tenant_id: str, **kwargs) -> Opening:
        """Create a new job opening with auto-generated slug."""
        title = kwargs["title"]
        base_slug = generate_slug(title)
        slug = base_slug

        # Ensure unique slug within tenant
        existing = await self._repo.get_by_slug(base_slug, tenant_id)
        if existing:
            import uuid
            slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

        # Handle profile creation if provided
        profile_data = kwargs.pop("profile", None)
        opening = Opening(tenant_id=tenant_id, slug=slug, **kwargs)
        opening = await self._repo.create(opening)

        if profile_data:
            profile = JobProfile(
                tenant_id=tenant_id,
                opening_id=opening.id,
                **profile_data.model_dump(),
            )
            await self._profile_repo.create(profile)

        return opening

    async def get_opening(self, opening_id: str, tenant_id: str) -> Optional[Opening]:
        return await self._repo.get(opening_id, tenant_id)

    async def list_openings(self, tenant_id: str) -> list[Opening]:
        return list(await self._repo.get_all(tenant_id=tenant_id))

    async def list_public_openings(self, tenant_id: str) -> list[Opening]:
        return list(await self._repo.list_public(tenant_id))

    async def update_opening(self, opening_id: str, tenant_id: str, **kwargs) -> Opening:
        opening = await self.get_opening(opening_id, tenant_id)
        if not opening:
            raise ValidationError(message="Opening not found", details={"opening_id": opening_id})

        allowed = {
            "title", "description", "requirements", "responsibilities",
            "department", "location", "employment_type", "salary_min",
            "salary_max", "salary_currency", "is_featured", "application_deadline",
            "sort_order", "meta", "published_at",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(opening, key, value)

        return await self._repo.update(opening)

    async def update_status(self, opening_id: str, tenant_id: str, status: str) -> Opening:
        opening = await self.get_opening(opening_id, tenant_id)
        if not opening:
            raise ValidationError(message="Opening not found", details={"opening_id": opening_id})

        from app.models.opening import OpeningStatus
        if status not in OpeningStatus.CHOICES:
            raise ValidationError(
                message=f"Invalid status: {status}",
                details={"allowed_statuses": OpeningStatus.CHOICES},
            )

        opening.status = status
        if status == OpeningStatus.ACTIVE and not opening.published_at:
            from datetime import datetime, timezone
            opening.published_at = datetime.now(timezone.utc)

        return await self._repo.update(opening)

    async def delete_opening(self, opening_id: str, tenant_id: str) -> None:
        opening = await self.get_opening(opening_id, tenant_id)
        if not opening:
            raise ValidationError(message="Opening not found", details={"opening_id": opening_id})
        await self._repo.soft_delete(opening_id, tenant_id)
