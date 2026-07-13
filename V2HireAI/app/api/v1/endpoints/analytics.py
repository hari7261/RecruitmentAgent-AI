"""
Analytics API endpoints.

GET /api/v1/admin/analytics          — platform-wide analytics (superadmin)
GET /api/v1/org/analytics            — org-level analytics (org_admin/member)
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_session,
)
from app.core.auth import get_current_tenant, get_current_superadmin, require_roles
from app.core.auth import RoleChecker
from app.models.tenant import Tenant
from app.models.application import Application, ApplicationStatus
from app.models.opening import Opening
from app.models.resume import Resume
from app.models.user import User
from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.application_repository import ApplicationRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/platform",
    summary="Platform analytics (superadmin only)",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def platform_analytics(
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenants = (await session.execute(select(func.count()).select_from(Tenant))).scalar_one() or 0
    active_tenants = (await session.execute(select(func.count()).select_from(Tenant).where(Tenant.is_active == True, Tenant.deleted_at.is_(None)))).scalar_one() or 0
    total_apps = (await session.execute(select(func.count()).select_from(Application))).scalar_one() or 0
    total_openings = (await session.execute(select(func.count()).select_from(Opening))).scalar_one() or 0
    total_resumes = (await session.execute(select(func.count()).select_from(Resume))).scalar_one() or 0
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one() or 0

    status_counts = {}
    for status in ApplicationStatus.CHOICES:
        count = (await session.execute(select(func.count()).select_from(Application).where(Application.status == status, Application.deleted_at.is_(None)))).scalar_one() or 0
        status_counts[status] = count

    mrr = 0.0
    subs = await session.execute(select(Subscription.amount, Subscription.status))
    for amount, status in subs.all():
        if status in ("active", "trialing", "past_due") and amount:
            mrr += amount

    return {
        "total_tenants": tenants,
        "active_tenants": active_tenants,
        "total_applications": total_apps,
        "total_openings": total_openings,
        "total_resumes": total_resumes,
        "total_users": total_users,
        "applications_by_status": status_counts,
        "mrr": round(mrr, 2),
    }


@router.get(
    "/org",
    summary="Organization analytics",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def org_analytics(
    current_tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.repositories.opening_repository import OpeningRepository
    from app.repositories.resume_repository import ResumeRepository

    opening_repo = OpeningRepository(session)
    resume_repo = ResumeRepository(session)
    app_repo = ApplicationRepository(session)

    openings = await opening_repo.get_all(tenant_id=current_tenant_id)
    total_openings = len(openings)
    active_openings = sum(1 for o in openings if o.status == "active")

    total_resumes = await resume_repo.count(tenant_id=current_tenant_id)

    analytics = await app_repo.get_analytics(current_tenant_id)
    total_apps = analytics.get("total", 0)

    return {
        "total_openings": total_openings,
        "active_openings": active_openings,
        "total_applications": total_apps,
        "total_resumes": total_resumes,
        "applications_by_status": analytics.get("by_status", {}),
    }
