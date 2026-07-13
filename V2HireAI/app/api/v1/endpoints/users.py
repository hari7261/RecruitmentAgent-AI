"""
User Management API endpoints — organization-scoped.

GET  /api/v1/users             → list org users
POST /api/v1/users             → add user to org (admin only)
DELETE /api/v1/users/{id}      → remove user
PATCH /api/v1/users/{id}/role  → change user role
POST /api/v1/users/invite      → invite new member
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_auth_service,
    get_session,
)
from app.core.auth import get_current_tenant, require_roles, get_current_user
from app.core.auth import RoleChecker
from app.core.exceptions import DuplicateResourceError, ValidationError
from app.models.user import UserRole, User
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import ErrorResponse, UserCreate, UserResponse, UserUpdate
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users in the current organization",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def list_org_users(
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> list[UserResponse]:
    repo = UserRepository(session)
    users = await repo.get_by_tenant(current_tenant_id)
    return [UserResponse.model_validate(u) for u in users]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new user to the organization",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def create_org_user(
    payload: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    current_tenant_id: str = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if payload.tenant_id and payload.tenant_id != current_tenant_id:
        raise ValidationError(message="Cannot create user in another tenant")

    # S3 Fix: Prevent privilege escalation - org_admin cannot create super_admin
    if current_user.role != "super_admin" and payload.role == "super_admin":
        raise ValidationError(
            message="Insufficient permissions to assign super_admin role",
            details={"allowed_roles": ["org_admin", "org_member"]},
        )

    # Validate role is allowed
    allowed_roles = ["org_admin", "org_member"] if current_user.role != "super_admin" else UserRole.CHOICES
    if payload.role not in allowed_roles:
        raise ValidationError(
            message="Invalid role for your permission level",
            details={"allowed_roles": allowed_roles},
        )

    user = await auth_service.create_user(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        tenant_id=current_tenant_id,
        full_name=payload.full_name,
    )
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def update_user_role(
    user_id: str,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    repo = UserRepository(session)
    user = await repo.get(user_id, tenant_id=current_tenant_id)
    if not user:
        raise ValidationError(message="User not found", details={"user_id": user_id})

    # S3 Fix: Prevent privilege escalation on role update
    if payload.role:
        if current_user.role != "super_admin" and payload.role == "super_admin":
            raise ValidationError(
                message="Insufficient permissions to assign super_admin role",
                details={"allowed_roles": ["org_admin", "org_member"]},
            )
        allowed_roles = ["org_admin", "org_member"] if current_user.role != "super_admin" else UserRole.CHOICES
        if payload.role not in allowed_roles:
            raise ValidationError(
                message="Invalid role for your permission level",
                details={"allowed_roles": allowed_roles},
            )
        user.role = payload.role
    
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    user = await repo.update(user)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from organization (soft delete)",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_tenant_id: str = Depends(get_current_tenant),
) -> None:
    repo = UserRepository(session)
    user = await repo.get(user_id, tenant_id=current_tenant_id)
    if not user:
        raise ValidationError(message="User not found", details={"user_id": user_id})
    await repo.soft_delete(user_id, tenant_id=current_tenant_id)
    return None


# ── Tenant/Org settings (M12/Settings fix) ─────────────────────────
from app.schemas.schemas import TenantResponse, TenantUpdate
from app.services.tenant_service import TenantService
from app.api.dependencies import get_tenant_service

@router.get(
    "/tenant/me",
    summary="Get current organization settings",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def get_my_tenant(
    current_tenant_id: str = Depends(get_current_tenant),
    tenant_service: TenantService = Depends(get_tenant_service),
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenant = await tenant_service.get_tenant(current_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Load subscription details (M12/Settings fix)
    from app.models.subscription import Subscription
    sub_res = await session.execute(
        select(Subscription).where(Subscription.tenant_id == current_tenant_id)
    )
    sub = sub_res.scalar_one_or_none()
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "description": tenant.description,
        "contact_email": tenant.contact_email,
        "contact_phone": tenant.contact_phone,
        "website": tenant.website,
        "logo_url": tenant.logo_url,
        "primary_color": tenant.primary_color,
        "custom_domain": tenant.custom_domain,
        "branding": tenant.branding or {},
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
        "subscription": {
            "plan": sub.plan if sub else "free",
            "status": sub.status if sub else "active",
            "resume_limit": sub.resume_limit if sub else 5,
            "resumes_used": sub.resumes_used_this_period if sub else 0,
            "user_limit": sub.user_limit if sub else 1,
            "amount": sub.amount if sub else 0,
            "next_billing_date": sub.next_billing_date if sub else None
        }
    }


@router.patch(
    "/tenant/me",
    response_model=TenantResponse,
    summary="Update current organization settings",
    dependencies=[Depends(require_roles(["super_admin", "org_admin"]))],
)
async def update_my_tenant(
    payload: TenantUpdate,
    current_tenant_id: str = Depends(get_current_tenant),
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("is_active", None)
    tenant = await tenant_service.update_tenant(current_tenant_id, **update_data)
    return TenantResponse.model_validate(tenant)
