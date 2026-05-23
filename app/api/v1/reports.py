"""
Report endpoints for flagging inappropriate content.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_admin
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportInternal,
    ReportListResponse,
    ReportPublic,
    ReportUpdate,
)
from app.utils.sanitize import sanitize_plain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportPublic, status_code=status.HTTP_201_CREATED)
async def submit_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportPublic:
    """Submit a report for inappropriate content (any authenticated user)."""
    report = Report(
        reporter_id=current_user.id,
        content_type=body.content_type,
        content_id=body.content_id,
        reason=sanitize_plain(body.reason),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Report submitted: id={report.id} "
        f"type={body.content_type} content_id={body.content_id} reporter={current_user.id}"
    )

    return ReportPublic.model_validate(report)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """List all reports (admin only)."""
    assert_admin(current_user)

    count_result = await db.execute(select(func.count()).select_from(Report))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Report)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    reports = result.scalars().all()

    return ReportListResponse(
        items=[ReportInternal.model_validate(r) for r in reports],
        total=total,
    )


@router.patch("/{report_id}", response_model=ReportInternal)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportInternal:
    """Update a report's status and/or admin notes (admin only)."""
    assert_admin(current_user)

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found."
        )

    if body.status is not None:
        report.status = body.status
    if body.admin_notes is not None:
        report.admin_notes = sanitize_plain(body.admin_notes)

    await db.flush()
    await db.refresh(report)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Report updated: id={report_id} admin={current_user.id}"
    )

    return ReportInternal.model_validate(report)
