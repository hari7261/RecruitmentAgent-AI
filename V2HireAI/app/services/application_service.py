"""
Application Service — orchestration for candidate application processing.

Handles the full candidate flow: validate opening → parse resume →
score against job profile → persist application → notify.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ValidationError,
    ParseError,
    SubscriptionLimitError,
)
from app.models.application import Application, ApplicationStatus, ApplicationSource
from app.models.user import UserRole
from app.repositories.application_repository import ApplicationRepository
from app.repositories.opening_repository import OpeningRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.ats_score_repository import ATSScoreRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.resume_service import ResumeService
from app.services.ats_service import ATSService

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service for managing candidate applications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._app_repo = ApplicationRepository(session)
        self._opening_repo = OpeningRepository(session)
        self._candidate_repo = CandidateRepository(session)
        self._resume_repo = ResumeRepository(session)
        self._score_repo = ATSScoreRepository(session)
        self._sub_repo = SubscriptionRepository(session)

    async def apply_to_opening(
        self,
        tenant_id: str,
        opening_id: str,
        user_id: Optional[str],
        upload_file,
        cover_letter: Optional[str] = None,
        source: str = ApplicationSource.DIRECT,
        # H8 Fix: Accept candidate identity overrides from form
        candidate_name: Optional[str] = None,
        candidate_email: Optional[str] = None,
        candidate_phone: Optional[str] = None,
    ) -> Application:
        """
        Process a candidate application:
        1. Validate opening is active
        2. Check subscription limits
        3. Parse resume via ResumeService
        4. Score against opening's job profile
        5. Create Application record
        6. Return application with score
        """
        # 1. Validate opening
        opening = await self._opening_repo.get(opening_id, tenant_id)
        if not opening:
            raise ValidationError(message="Job opening not found", details={"opening_id": opening_id})

        if opening.status != "active":
            raise ValidationError(
                message="This job opening is not accepting applications",
                details={"status": opening.status},
            )

        # 2. Check subscription status
        subscription = await self._sub_repo.get_by_tenant(tenant_id)
        if subscription:
            from app.models.subscription import SubscriptionStatus
            if subscription.status == SubscriptionStatus.SUSPENDED:
                raise SubscriptionLimitError(message="Subscription is suspended")
            # Monthly resume limit enforcement is temporarily disabled.

        normalized_candidate_name = candidate_name.strip() if candidate_name else None
        normalized_candidate_email = candidate_email.strip().lower() if candidate_email else None
        normalized_candidate_phone = candidate_phone.strip() if candidate_phone else None

        if normalized_candidate_email:
            existing_candidate = await self._candidate_repo.get_by_email(
                normalized_candidate_email,
                tenant_id=tenant_id,
            )
            if existing_candidate:
                existing_application = await self._app_repo.get_by_opening_candidate(
                    opening.id,
                    existing_candidate.id,
                    tenant_id,
                )
                if existing_application:
                    raise ValidationError(
                        message="You have already applied for this job",
                        details={
                            "opening_id": opening.id,
                            "application_id": existing_application.id,
                        },
                    )

        # 3. Resolve the job profile for the opening
        from app.repositories.job_profile_repository import JobProfileRepository
        profile_repo = JobProfileRepository(self._session)
        job_profile = await profile_repo.get_by_opening(opening.id, tenant_id)
        if not job_profile:
            job_profile = await profile_repo.get_default(tenant_id)
        if not job_profile:
            job_profile = "default"

        # 4. Parse resume (with tenant_id for data isolation and custom job profile)
        resume_service = ResumeService(self._session)

        resume = await resume_service.upload_and_process(
            upload_file,
            job_profile=job_profile,
            tenant_id=tenant_id,
            candidate_name=normalized_candidate_name,
            candidate_email=normalized_candidate_email,
            candidate_phone=normalized_candidate_phone,
        )

        # H8 Fix: Apply form-submitted identity if parsing missed it
        if resume.candidate_id:
            candidate = await self._candidate_repo.get(resume.candidate_id, tenant_id=tenant_id)
            if candidate:
                if normalized_candidate_name and not candidate.name:
                    candidate.name = normalized_candidate_name
                if normalized_candidate_email and not candidate.email:
                    candidate.email = normalized_candidate_email
                if normalized_candidate_phone and not candidate.phone:
                    candidate.phone = normalized_candidate_phone
                await self._candidate_repo.update(candidate)

        existing_application = await self._app_repo.get_by_opening_candidate(
            opening.id,
            resume.candidate_id,
            tenant_id,
        )
        if existing_application:
            raise ValidationError(
                message="You have already applied for this job",
                details={
                    "opening_id": opening.id,
                    "application_id": existing_application.id,
                },
            )

        # 5. Score against opening profile
        ats_service = ATSService(self._session)
        score = await ats_service.get_score_by_resume_id(resume.id, tenant_id=tenant_id)

        # 5. Create application
        application = Application(
            tenant_id=tenant_id,
            opening_id=opening.id,
            candidate_id=resume.candidate_id,
            resume_id=resume.id,
            ats_score_id=score.id,
            cover_letter=cover_letter,
            source=source,
            status=ApplicationStatus.APPLIED,
            total_score=score.total_score,
            recommendation=score.recommendation,
            applied_at=datetime.now(timezone.utc),
        )
        application = await self._app_repo.create(application)

        # Increment usage for reporting only
        if subscription:
            await self._sub_repo.increment_resumes_used(subscription.id, 1)

        logger.info(
            "Application created: candidate=%s opening=%s score=%.1f",
            resume.candidate_id, opening.id, score.total_score,
        )
        return application

    async def get_application(
        self, application_id: str, tenant_id: str
    ) -> Optional[Application]:
        return await self._app_repo.get_by_id(application_id, tenant_id)

    async def list_applications(
        self, opening_id: str, tenant_id: str, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[Application], int]:
        offset = (page - 1) * page_size
        apps = await self._app_repo.list_by_opening(
            opening_id, tenant_id, offset=offset, limit=page_size
        )
        total = await self._app_repo.count_by_opening(opening_id, tenant_id)
        return list(apps), total

    async def list_candidate_applications(
        self, candidate_id: str
    ) -> list[Application]:
        return list(await self._app_repo.list_by_candidate(candidate_id))

    async def update_status(
        self, application_id: str, tenant_id: str, new_status: str, notes: Optional[str] = None
    ) -> Application:
        from app.models.application_status_history import ApplicationStatusHistory
        application = await self.get_application(application_id, tenant_id)
        if not application:
            raise ValidationError(
                message="Application not found", details={"application_id": application_id}
            )

        old_status = application.status
        application.status = new_status
        application.status_changed_at = datetime.now(timezone.utc)
        if notes:
            application.admin_notes = (application.admin_notes or "") + f"\n[{new_status}] {notes}"

        await self._app_repo.update(application)

        # Add history entry
        history = ApplicationStatusHistory(
            application_id=application.id,
            from_status=old_status,
            to_status=new_status,
            changed_by="admin",
            notes=notes,
        )
        self._session.add(history)
        await self._session.flush()

        return application

    async def add_note(self, application_id: str, tenant_id: str, notes: str) -> Application:
        application = await self.get_application(application_id, tenant_id)
        if not application:
            raise ValidationError(
                message="Application not found", details={"application_id": application_id}
            )
        application.admin_notes = (application.admin_notes or "") + f"\n{notes}"
        return await self._app_repo.update(application)

    async def add_tag(self, application_id: str, tenant_id: str, tag: str) -> Application:
        application = await self.get_application(application_id, tenant_id)
        if not application:
            raise ValidationError(
                message="Application not found", details={"application_id": application_id}
            )
        tags = application.tags or []
        if tag not in tags:
            tags.append(tag)
            application.tags = tags
        return await self._app_repo.update(application)
