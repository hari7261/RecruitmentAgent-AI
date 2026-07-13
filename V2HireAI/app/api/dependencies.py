"""
Shared service providers for FastAPI dependency injection.
"""
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService
from app.services.opening_service import OpeningService
from app.services.application_service import ApplicationService
from app.services.public_service import PublicService
from app.services.resume_service import ResumeService
from app.services.ats_service import ATSService


async def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[AuthService, None]:
    yield AuthService(session)


async def get_tenant_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[TenantService, None]:
    yield TenantService(session)


async def get_opening_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[OpeningService, None]:
    yield OpeningService(session)


async def get_application_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[ApplicationService, None]:
    yield ApplicationService(session)


async def get_public_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[PublicService, None]:
    yield PublicService(session)


async def get_resume_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[ResumeService, None]:
    yield ResumeService(session)


async def get_ats_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[ATSService, None]:
    yield ATSService(session)
