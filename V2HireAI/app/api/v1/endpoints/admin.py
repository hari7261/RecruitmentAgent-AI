"""
Admin tenant management endpoints — super_admin only.

POST /api/v1/admin/tenants               → create org
GET  /api/v1/admin/tenants               → list all orgs
GET  /api/v1/admin/tenants/{id}          → org detail
PATCH /api/v1/admin/tenants/{id}         → update org
DELETE /api/v1/admin/tenants/{id}        → delete org
POST /api/v1/admin/tenants/{id}/users    → add user to org
POST /api/v1/admin/tenants/{id}/subscription → set subscription plan
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session, get_tenant_service
from app.core.auth import get_current_superadmin
from app.core.auth import RoleChecker
from app.core.config import settings
from app.core.exceptions import DuplicateResourceError, ValidationError
from app.models.user import UserRole
from app.models.subscription import PlanType, SubscriptionStatus
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.schemas import (
    ErrorResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/tenants", tags=["Admin - Tenants"])


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="List all organizations",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def list_tenants(
    current_user=Depends(get_current_superadmin),
    tenant_service: TenantService = Depends(get_tenant_service),
) -> list[TenantResponse]:
    tenants = await tenant_service.list_tenants()
    return [TenantResponse.model_validate(t) for t in tenants]


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def create_tenant(
    payload: TenantCreate,
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = await tenant_service.create_tenant(
        name=payload.name,
        slug=payload.slug,
        contact_email=payload.contact_email,
        description=payload.description,
        contact_phone=payload.contact_phone,
        website=payload.website,
        logo_url=payload.logo_url,
        primary_color=payload.primary_color,
        custom_domain=payload.custom_domain,
        branding=payload.branding,
    )
    return TenantResponse.model_validate(tenant)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get organization detail",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def get_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant:
        raise ValidationError(message="Tenant not found", details={"tenant_id": tenant_id})
    return TenantResponse.model_validate(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update organization",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def update_tenant(
    tenant_id: str,
    payload: TenantUpdate,
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    update_data = payload.model_dump(exclude_unset=True)
    tenant = await tenant_service.update_tenant(tenant_id, **update_data)
    return TenantResponse.model_validate(tenant)


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization (soft delete)",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def delete_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
    session: AsyncSession = Depends(get_session),
) -> None:
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant:
        raise ValidationError(message="Tenant not found", details={"tenant_id": tenant_id})
    await tenant_service._repo.soft_delete(tenant_id)
    return None


@router.post(
    "/{tenant_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add user to organization",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def add_user_to_tenant(
    tenant_id: str,
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    if payload.tenant_id and payload.tenant_id != tenant_id:
        raise ValidationError(message="User tenant_id mismatch")

    auth = AuthService(session)
    if payload.role not in UserRole.CHOICES:
        raise ValidationError(
            message="Invalid role",
            details={"allowed_roles": UserRole.CHOICES},
        )
    user = await auth.create_user(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        tenant_id=tenant_id,
        full_name=payload.full_name,
    )
    return UserResponse.model_validate(user)


@router.post(
    "/{tenant_id}/subscription",
    response_model=SubscriptionResponse,
    summary="Update tenant subscription",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def update_subscription(
    tenant_id: str,
    payload: SubscriptionUpdate,
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    repo = SubscriptionRepository(session)
    sub = await repo.get_by_tenant(tenant_id)
    if not sub:
        raise ValidationError(message="Subscription not found for this tenant")

    # M8 Fix: Use typed schema with validation
    update_data = payload.model_dump(exclude_unset=True)
    
    # Validate plan and status enums
    if "plan" in update_data and update_data["plan"] not in PlanType.CHOICES:
        raise ValidationError(
            message="Invalid plan",
            details={"allowed_plans": PlanType.CHOICES},
        )
    if "status" in update_data and update_data["status"] not in SubscriptionStatus.CHOICES:
        raise ValidationError(
            message="Invalid status",
            details={"allowed_statuses": SubscriptionStatus.CHOICES},
        )
    
    # Apply updates
    for key, value in update_data.items():
        setattr(sub, key, value)

    sub = await repo.update(sub)
    return SubscriptionResponse.model_validate(sub)


# ── New: Cross-tenant listing endpoints (B-mock fix) ────────────────────────

@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users across all tenants (superadmin)",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def list_all_users(
    session: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    """Return all users from all tenants for the platform admin dashboard."""
    from app.repositories.user_repository import UserRepository
    repo = UserRepository(session)
    users = await repo.get_all(limit=500, allow_unscoped=True)
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/subscriptions",
    response_model=list[SubscriptionResponse],
    summary="List all subscriptions across all tenants (superadmin)",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def list_all_subscriptions(
    session: AsyncSession = Depends(get_session),
) -> list[SubscriptionResponse]:
    """Return all subscriptions for the platform admin dashboard."""
    repo = SubscriptionRepository(session)
    subs = await repo.get_all(limit=500, allow_unscoped=True)
    return [SubscriptionResponse.model_validate(s) for s in subs]


@router.get(
    "/platform-settings",
    summary="Get platform settings metadata (superadmin)",
    dependencies=[Depends(RoleChecker(["super_admin"]))],
)
async def get_platform_settings() -> dict:
    return {
        "platform_name": settings.platform_name,
        "support_email": settings.platform_support_email,
        "default_plan": settings.default_plan,
        "app_version": settings.app_version,
    }
