"""
Editorial workflow endpoints — editor+ only.

Status transition rules (enforced here):
  submitted       -> under_review       (editor assigns)
  under_review    -> revision_requested, accepted, rejected
  revision_requested -> submitted       (contributor resubmits — done in /submissions)
  accepted        -> published          (via /publish endpoint, creates Article)
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_editor
from app.models.article import Article, ArticleStatus
from app.models.submission import (
    ALLOWED_TRANSITIONS,
    EditorialNote,
    Submission,
    SubmissionStatus,
)
from app.models.user import User, UserRole
from app.schemas.article import ArticleInternal
from app.schemas.editorial import (
    EditorialNoteCreate,
    EditorialNoteListResponse,
    EditorialNotePublic,
)
from app.schemas.submission import (
    AssignEditorRequest,
    EditorialSubmissionListResponse,
    StatusUpdateRequest,
    SubmissionInternal,
)
from app.utils.sanitize import sanitize_html, sanitize_plain
from app.services.email import send_submission_status_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/editorial", tags=["Editorial"])


@router.get("/submissions", response_model=EditorialSubmissionListResponse)
async def list_editorial_submissions(
    skip: int = 0,
    limit: int = 50,
    submission_status: SubmissionStatus | None = Query(None, alias="status"),
    category: str | None = None,
    issue_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditorialSubmissionListResponse:
    """List all submissions with optional filters (editor+ only)."""
    assert_editor(current_user)

    query = select(Submission)
    count_query = select(func.count()).select_from(Submission)

    filters = []
    if submission_status:
        filters.append(Submission.status == submission_status)
    if category:
        filters.append(Submission.category == category)
    if issue_id:
        filters.append(Submission.issue_id == issue_id)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Submission.submitted_at.desc().nullslast(), Submission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    submissions = result.scalars().all()

    return EditorialSubmissionListResponse(
        items=[SubmissionInternal.model_validate(s) for s in submissions],
        total=total,
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionInternal)
async def get_editorial_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionInternal:
    """Get full submission detail for editorial review (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.editorial_notes))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    return SubmissionInternal.model_validate(submission)


@router.patch("/submissions/{submission_id}/status", response_model=SubmissionInternal)
async def update_submission_status(
    submission_id: uuid.UUID,
    body: StatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionInternal:
    """
    Update submission status with transition validation (editor+ only).
    Allowed transitions:
      submitted -> under_review
      under_review -> revision_requested | accepted | rejected
      accepted -> published (use /publish endpoint instead for full flow)
    """
    assert_editor(current_user)

    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    allowed = ALLOWED_TRANSITIONS.get(submission.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition from '{submission.status.value}' to '{body.status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            ),
        )

    old_status = submission.status
    submission.status = body.status
    submission.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Submission status changed: "
        f"id={submission_id} {old_status}->{body.status} by editor={current_user.id}"
    )

    # Notify contributor of status change
    contributor_result = await db.execute(
        select(User).where(User.id == submission.contributor_id)
    )
    contributor = contributor_result.scalar_one_or_none()
    if contributor:
        await send_submission_status_email(
            contributor.email, submission.title, body.status.value
        )

    return SubmissionInternal.model_validate(submission)


@router.post("/submissions/{submission_id}/assign", response_model=SubmissionInternal)
async def assign_editor(
    submission_id: uuid.UUID,
    body: AssignEditorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionInternal:
    """
    Assign an editor to a submission and move it to under_review (editor+ only).
    The assigned editor must have editor or admin role.
    """
    assert_editor(current_user)

    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    # Validate that the editor being assigned has the right role
    editor_result = await db.execute(
        select(User).where(User.id == body.editor_id, User.deleted_at.is_(None))
    )
    editor = editor_result.scalar_one_or_none()
    if not editor or editor.role not in {UserRole.editor, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must be an editor or admin.",
        )

    # Assignment moves submitted -> under_review
    if submission.status == SubmissionStatus.submitted:
        submission.status = SubmissionStatus.under_review

    submission.assigned_editor_id = body.editor_id
    submission.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Editor assigned: submission={submission_id} editor={body.editor_id}"
    )

    return SubmissionInternal.model_validate(submission)


@router.post("/submissions/{submission_id}/notes", response_model=EditorialNotePublic, status_code=status.HTTP_201_CREATED)
async def add_editorial_note(
    submission_id: uuid.UUID,
    body: EditorialNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditorialNotePublic:
    """Add a private editorial note to a submission (editor+ only)."""
    assert_editor(current_user)

    sub_result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    note = EditorialNote(
        submission_id=submission_id,
        editor_id=current_user.id,
        note=sanitize_plain(body.note),
        created_at=datetime.now(timezone.utc),
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)

    return EditorialNotePublic.model_validate(note)


@router.get("/submissions/{submission_id}/notes", response_model=EditorialNoteListResponse)
async def list_editorial_notes(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditorialNoteListResponse:
    """List all editorial notes for a submission (editor+ only)."""
    assert_editor(current_user)

    sub_result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    result = await db.execute(
        select(EditorialNote)
        .where(EditorialNote.submission_id == submission_id)
        .order_by(EditorialNote.created_at.asc())
    )
    notes = result.scalars().all()

    return EditorialNoteListResponse(
        items=[EditorialNotePublic.model_validate(n) for n in notes],
        total=len(notes),
    )


@router.post("/submissions/{submission_id}/publish", response_model=ArticleInternal, status_code=status.HTTP_201_CREATED)
async def publish_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleInternal:
    """
    Convert an accepted submission into a published Article.

    Publish flow:
    1. Validate submission is in 'accepted' status.
    2. Create Article from submission data.
    3. Generate a unique slug from title.
    4. Set submission status to 'published'.
    5. Return the created Article.
    """
    assert_editor(current_user)

    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if submission.status != SubmissionStatus.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only accepted submissions can be published. Current status: '{submission.status.value}'.",
        )

    # Generate unique slug
    base_slug = slugify(submission.title)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(
            select(Article).where(Article.slug == slug)
        )
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    article = Article(
        submission_id=submission.id,
        title=submission.title,
        slug=slug,
        body=submission.body_text,
        category=submission.category.value,
        contributor_id=submission.contributor_id,
        anonymous_byline=submission.anonymous_byline,
        byline_name=None,
        issue_id=submission.issue_id,
        content_warnings=submission.content_warnings,
        status=ArticleStatus.published,
        published_at=datetime.now(timezone.utc),
        featured=False,
    )
    db.add(article)

    submission.status = SubmissionStatus.published
    submission.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(article)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Article published: id={article.id} slug={slug} "
        f"from submission={submission_id} by editor={current_user.id}"
    )

    # Notify contributor
    contributor_result = await db.execute(
        select(User).where(User.id == submission.contributor_id)
    )
    contributor = contributor_result.scalar_one_or_none()
    if contributor:
        await send_submission_status_email(
            contributor.email, submission.title, "published"
        )

    # Build byline for response
    byline = article.byline_name or "Anonymous" if article.anonymous_byline else ""

    return ArticleInternal(
        id=article.id,
        submission_id=article.submission_id,
        title=article.title,
        slug=article.slug,
        excerpt=article.excerpt,
        body=article.body,
        category=article.category,
        contributor_id=article.contributor_id,
        byline=byline,
        anonymous_byline=article.anonymous_byline,
        byline_name=article.byline_name,
        issue_id=article.issue_id,
        content_warnings=article.content_warnings,
        status=article.status,
        published_at=article.published_at,
        scheduled_for=article.scheduled_for,
        featured=article.featured,
        tags=[],
        created_at=article.created_at,
        updated_at=article.updated_at,
    )
