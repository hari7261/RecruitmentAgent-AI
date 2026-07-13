"""
Application repository — tenant-scoped candidate application queries.
"""
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Application, session)

    async def get_by_id(
        self, application_id: str, tenant_id: str
    ) -> Optional[Application]:
        result = await self._session.execute(
            select(Application).where(
                Application.id == application_id,
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_opening(
        self, opening_id: str, tenant_id: str, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Application]:
        result = await self._session.execute(
            select(Application)
            .where(
                Application.opening_id == opening_id,
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
            .order_by(Application.total_score.desc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_by_opening(self, opening_id: str, tenant_id: str) -> int:
        from sqlalchemy import select as sa_select
        result = await self._session.execute(
            sa_select(func.count())
            .select_from(Application)
            .where(
                Application.opening_id == opening_id,
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
        )
        return result.scalar_one() or 0

    async def list_by_candidate(
        self, candidate_id: str
    ) -> Sequence[Application]:
        result = await self._session.execute(
            select(Application)
            .where(
                Application.candidate_id == candidate_id,
                Application.deleted_at.is_(None),
            )
            .order_by(Application.applied_at.desc())
        )
        return result.scalars().all()

    async def get_by_opening_candidate(
        self, opening_id: str, candidate_id: str, tenant_id: str
    ) -> Optional[Application]:
        result = await self._session.execute(
            select(Application).where(
                Application.opening_id == opening_id,
                Application.candidate_id == candidate_id,
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_smart_shortlist(
        self, tenant_id: str, min_score: float = 75.0, limit: int = 50
    ) -> list[tuple[Application, "Opening"]]:
        from app.models.opening import Opening
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(Application, Opening)
            .join(Opening, Opening.id == Application.opening_id)
            .where(
                Application.tenant_id == tenant_id,
                Application.total_score >= min_score,
                Application.deleted_at.is_(None),
                Opening.deleted_at.is_(None),
            )
            .order_by(Application.total_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def list_all_with_details(
        self, tenant_id: str, *, limit: int = 200
    ) -> list[dict]:
        """
        Return all applications for a tenant, enriched with candidate
        name/email, opening title, and ATS score breakdown.
        Single query via JOINs — no N+1.
        """
        from sqlalchemy import select as sa_select
        from app.models.candidate import Candidate
        from app.models.opening import Opening
        from app.models.ats_score import ATSScore

        stmt = (
            sa_select(
                Application.id,
                Application.opening_id,
                Application.candidate_id,
                Application.resume_id,
                Application.ats_score_id,
                Application.status,
                Application.total_score,
                Application.recommendation,
                Application.cover_letter,
                Application.source,
                Application.applied_at,
                Candidate.name.label("candidate_name"),
                Candidate.email.label("candidate_email"),
                Candidate.phone.label("candidate_phone"),
                Opening.title.label("opening_title"),
                Opening.slug.label("opening_slug"),
                ATSScore.skill_score,
                ATSScore.experience_score,
                ATSScore.education_score,
                ATSScore.certification_score,
                ATSScore.project_score,
                ATSScore.matched_skills_count,
                ATSScore.missing_skills_count,
                ATSScore.total_experience_months,
            )
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(Opening, Opening.id == Application.opening_id)
            .outerjoin(ATSScore, ATSScore.resume_id == Application.resume_id)
            .where(
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
            .order_by(Application.applied_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def list_by_candidate_ids_with_details(
        self, candidate_ids: list[str], *, limit: int = 200
    ) -> list[dict]:
        from sqlalchemy import select as sa_select
        from app.models.candidate import Candidate
        from app.models.opening import Opening

        if not candidate_ids:
            return []

        stmt = (
            sa_select(
                Application.id,
                Application.tenant_id,
                Application.opening_id,
                Application.candidate_id,
                Application.resume_id,
                Application.status,
                Application.total_score,
                Application.recommendation,
                Application.applied_at,
                Application.updated_at,
                Candidate.name.label("candidate_name"),
                Candidate.email.label("candidate_email"),
                Opening.title.label("opening_title"),
                Opening.slug.label("opening_slug"),
            )
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(Opening, Opening.id == Application.opening_id)
            .where(
                Application.candidate_id.in_(candidate_ids),
                Application.deleted_at.is_(None),
            )
            .order_by(Application.applied_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_analytics(self, tenant_id: str) -> dict:
        from sqlalchemy import select as sa_select
        counts = {}
        for status in ApplicationStatus.CHOICES:
            result = await self._session.execute(
                sa_select(func.count())
                .select_from(Application)
                .where(
                    Application.tenant_id == tenant_id,
                    Application.status == status,
                    Application.deleted_at.is_(None),
                )
            )
            counts[status] = result.scalar_one() or 0

        result = await self._session.execute(
            sa_select(func.count())
            .select_from(Application)
            .where(
                Application.tenant_id == tenant_id,
                Application.deleted_at.is_(None),
            )
        )
        total = result.scalar_one() or 0
        return {"total": total, "by_status": counts}
