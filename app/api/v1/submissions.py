"""
Submission management for contributors.
Contributors can create, view, update, and submit their own submissions.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_contributor
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionPublic,
    SubmissionUpdate,
)
from app.utils.sanitize import sanitize_html, sanitize_plain
from app.services.email import send_submission_received_email
from app.services.storage import save_file, delete_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("", response_model=SubmissionPublic, status_code=status.HTTP_201_CREATED)
async def create_submission(
    body: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """Create a new submission (contributor+ role required)."""
    assert_contributor(current_user)

    submission = Submission(
        contributor_id=current_user.id,
        title=sanitize_plain(body.title),
        category=body.category,
        issue_id=body.issue_id,
        body_text=sanitize_html(body.body_text),
        file_metadata=body.file_metadata,
        content_warnings=body.content_warnings or [],
        anonymous_byline=body.anonymous_byline,
        author_note=sanitize_plain(body.author_note),
        status=SubmissionStatus.draft,
    )
    db.add(submission)
    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Submission created: id={submission.id} user={current_user.id}"
    )

    return SubmissionPublic.model_validate(submission)


@router.get("/mine", response_model=SubmissionListResponse)
async def list_my_submissions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionListResponse:
    """List all submissions by the current user."""
    count_result = await db.execute(
        select(func.count())
        .select_from(Submission)
        .where(Submission.contributor_id == current_user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Submission)
        .where(Submission.contributor_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    submissions = result.scalars().all()

    return SubmissionListResponse(
        items=[SubmissionPublic.model_validate(s) for s in submissions],
        total=total,
    )


@router.get("/{submission_id}", response_model=SubmissionPublic)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """Get a specific submission (own submissions only)."""
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    return SubmissionPublic.model_validate(submission)


@router.patch("/{submission_id}", response_model=SubmissionPublic)
async def update_submission(
    submission_id: uuid.UUID,
    body: SubmissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """Update a draft submission. Only drafts can be edited."""
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if submission.status != SubmissionStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft submissions can be edited.",
        )

    if body.title is not None:
        submission.title = sanitize_plain(body.title)
    if body.category is not None:
        submission.category = body.category
    if body.issue_id is not None:
        submission.issue_id = body.issue_id
    if body.body_text is not None:
        submission.body_text = sanitize_html(body.body_text)
    if body.file_metadata is not None:
        submission.file_metadata = body.file_metadata
    if body.content_warnings is not None:
        submission.content_warnings = body.content_warnings
    if body.anonymous_byline is not None:
        submission.anonymous_byline = body.anonymous_byline
    if body.author_note is not None:
        submission.author_note = sanitize_plain(body.author_note)

    await db.flush()
    await db.refresh(submission)

    return SubmissionPublic.model_validate(submission)


@router.post("/{submission_id}/submit", response_model=SubmissionPublic)
async def submit_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """
    Change a draft submission to 'submitted' status.
    Also handles revision_requested -> submitted (resubmission after revision request).
    """
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    allowed_from = {SubmissionStatus.draft, SubmissionStatus.revision_requested}
    if submission.status not in allowed_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit a submission with status '{submission.status.value}'.",
        )

    submission.status = SubmissionStatus.submitted
    submission.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Submission submitted: id={submission.id}"
    )

    await send_submission_received_email(current_user.email, submission.title)

    return SubmissionPublic.model_validate(submission)


@router.post("/{submission_id}/upload", response_model=SubmissionPublic)
async def upload_file(
    submission_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """
    Attach a file to a draft submission (contributor+ role required).

    Accepted types: JPEG, PNG, GIF, WebP, PDF.
    Max size: configured via MAX_FILE_SIZE_MB (default 20MB).

    Only one file per submission — uploading again replaces the existing file.
    Only drafts can receive file uploads; submitted/accepted pieces are locked.
    """
    assert_contributor(current_user)

    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if submission.status != SubmissionStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Files can only be uploaded to draft submissions.",
        )

    # Delete previous file if one exists
    if submission.file_metadata:
        await delete_file(submission.file_metadata)

    metadata = await save_file(file, submission_id)
    submission.file_metadata = metadata

    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] File uploaded: submission={submission_id} "
        f"file={metadata['storage_key']} size={metadata['size_bytes']}B user={current_user.id}"
    )

    return SubmissionPublic.model_validate(submission)


@router.delete("/{submission_id}/file", response_model=SubmissionPublic)
async def remove_file(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    """Remove the attached file from a draft submission."""
    assert_contributor(current_user)

    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if submission.status != SubmissionStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Files can only be removed from draft submissions.",
        )

    if not submission.file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This submission has no attached file.",
        )

    await delete_file(submission.file_metadata)
    submission.file_metadata = None

    await db.flush()
    await db.refresh(submission)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] File removed: submission={submission_id} user={current_user.id}"
    )

    return SubmissionPublic.model_validate(submission)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a draft submission (only drafts can be deleted)."""
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.contributor_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if submission.status != SubmissionStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft submissions can be deleted.",
        )

    await db.delete(submission)
    await db.flush()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Submission deleted: id={submission_id} user={current_user.id}"
    )
