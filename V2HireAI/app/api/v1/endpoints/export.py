"""
Export API endpoints.

GET /api/v1/export/applications/{opening_id} → CSV export
GET /api/v1/export/openings → CSV export

B4 Fix: Use explicit JOINs to get candidate/resume data instead of ORM
        relationships that don't exist on Application model.
"""
import csv
import io
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.core.auth import get_current_tenant, require_roles
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.opening import Opening

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])


@router.get(
    "/applications/{opening_id}",
    summary="Export applications for an opening as CSV",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def export_applications(
    opening_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    # B4 Fix: Use an explicit JOIN to get candidate data — no ORM relationship needed
    stmt = (
        select(
            Application.id,
            Application.status,
            Application.total_score,
            Application.recommendation,
            Application.applied_at,
            Application.source,
            Candidate.name.label("candidate_name"),
            Candidate.email.label("candidate_email"),
            Candidate.phone.label("candidate_phone"),
        )
        .join(Candidate, Candidate.id == Application.candidate_id)
        .where(
            Application.opening_id == opening_id,
            Application.tenant_id == current_tenant_id,
            Application.deleted_at.is_(None),
        )
        .order_by(Application.total_score.desc().nulls_last())
    )
    result = await session.execute(stmt)
    rows = result.mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Candidate", "Email", "Phone", "Score", "Recommendation",
        "Status", "Source", "Applied At"
    ])
    for row in rows:
        writer.writerow([
            row["candidate_name"] or "",
            row["candidate_email"] or "",
            row["candidate_phone"] or "",
            row["total_score"] or "",
            row["recommendation"] or "",
            row["status"],
            row["source"] or "",
            row["applied_at"].strftime("%Y-%m-%d %H:%M") if row["applied_at"] else "",
        ])

    output.seek(0)
    filename = f"applications_{opening_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/openings",
    summary="Export openings as CSV",
    dependencies=[Depends(require_roles(["super_admin", "org_admin", "org_member"]))],
)
async def export_openings(
    current_tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    from app.repositories.opening_repository import OpeningRepository
    repo = OpeningRepository(session)
    openings = await repo.get_all(tenant_id=current_tenant_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Title", "Department", "Location", "Type", "Status", "Created At"
    ])
    for opening in openings:
        writer.writerow([
            opening.title,
            opening.department or "",
            opening.location or "",
            opening.employment_type or "",
            opening.status,
            opening.created_at.strftime("%Y-%m-%d") if opening.created_at else "",
        ])

    output.seek(0)
    filename = f"openings_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
