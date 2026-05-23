"""
Issue management endpoints.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from slugify import slugify
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_editor
from app.models.article import Article, ArticleStatus
from app.models.issue import Issue, IssueStatus
from app.models.user import User
from app.schemas.issue import (
    IssueCreate,
    IssueListResponse,
    IssuePublic,
    IssueStatusUpdate,
    IssueUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.get("", response_model=IssueListResponse)
async def list_issues(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> IssueListResponse:
    """List published issues (public)."""
    count_result = await db.execute(
        select(func.count())
        .select_from(Issue)
        .where(Issue.status == IssueStatus.published)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Issue)
        .where(Issue.status == IssueStatus.published)
        .order_by(Issue.publication_date.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    issues = result.scalars().all()

    return IssueListResponse(
        items=[IssuePublic.model_validate(i) for i in issues],
        total=total,
    )


@router.get("/{slug}", response_model=IssuePublic)
async def get_issue(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> IssuePublic:
    """Get a published issue by slug with its articles (public)."""
    result = await db.execute(
        select(Issue).where(Issue.slug == slug, Issue.status == IssueStatus.published)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found."
        )

    return IssuePublic.model_validate(issue)


@router.post("", response_model=IssuePublic, status_code=status.HTTP_201_CREATED)
async def create_issue(
    body: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IssuePublic:
    """Create a new issue (editor+ only)."""
    assert_editor(current_user)

    base_slug = slugify(body.title)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(Issue).where(Issue.slug == slug))
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    issue = Issue(
        title=body.title,
        slug=slug,
        theme_description=body.theme_description,
        editors_letter=body.editors_letter,
        cover_image_metadata=body.cover_image_metadata,
        submission_deadline=body.submission_deadline,
        publication_date=body.publication_date,
        status=body.status,
    )
    db.add(issue)
    await db.flush()
    await db.refresh(issue)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Issue created: id={issue.id} slug={slug}"
    )

    return IssuePublic.model_validate(issue)


@router.patch("/{issue_id}", response_model=IssuePublic)
async def update_issue(
    issue_id: uuid.UUID,
    body: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IssuePublic:
    """Update an issue (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found."
        )

    if body.title is not None:
        issue.title = body.title
    if body.theme_description is not None:
        issue.theme_description = body.theme_description
    if body.editors_letter is not None:
        issue.editors_letter = body.editors_letter
    if body.cover_image_metadata is not None:
        issue.cover_image_metadata = body.cover_image_metadata
    if body.submission_deadline is not None:
        issue.submission_deadline = body.submission_deadline
    if body.publication_date is not None:
        issue.publication_date = body.publication_date

    await db.flush()
    await db.refresh(issue)

    return IssuePublic.model_validate(issue)


@router.patch("/{issue_id}/status", response_model=IssuePublic)
async def update_issue_status(
    issue_id: uuid.UUID,
    body: IssueStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IssuePublic:
    """Update issue status (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found."
        )

    issue.status = body.status
    await db.flush()
    await db.refresh(issue)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Issue status updated: id={issue_id} status={body.status}"
    )

    return IssuePublic.model_validate(issue)
