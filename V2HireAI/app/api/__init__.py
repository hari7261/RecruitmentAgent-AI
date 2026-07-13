"""
API package init.
"""
from app.api.v1.endpoints import auth, admin, openings, applications, profiles, users, public
from app.api.dependencies import (
    get_auth_service,
    get_tenant_service,
    get_opening_service,
    get_application_service,
    get_public_service,
    get_resume_service,
    get_ats_service,
)
from app.core.auth import (
    get_current_user,
    get_current_superadmin,
    get_current_tenant,
    require_roles,
    RoleChecker,
)

__all__ = [
    "auth",
    "admin",
    "openings",
    "applications",
    "profiles",
    "users",
    "public",
    "get_auth_service",
    "get_tenant_service",
    "get_opening_service",
    "get_application_service",
    "get_public_service",
    "get_resume_service",
    "get_ats_service",
    "get_current_user",
    "get_current_superadmin",
    "get_current_tenant",
    "require_roles",
    "RoleChecker",
]
