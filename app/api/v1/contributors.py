"""
Contributor profile endpoints.

Privacy rules enforced here:
- Public listing and individual profile views use ContributorPublic schema,
  which never includes condition_identity.
- /contributors/me uses ContributorPrivate schema, which includes the field.
- No other endpoint returns condition_identity, period.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.contributor import ContributorProfile, ContributorStatus
from app.models.user import User, UserRole
from app.schemas.contributor import (
    ContributorCreate,
    ContributorListResponse,
    ContributorPrivate,
    ContributorPublic,
    ContributorUpdate,
)
from app.utils.sanitize import sanitize_html, sanitize_plain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contributors", tags=["Contributors"])


@router.get("", response_model=ContributorListResponse)
async def list_contributors(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> ContributorListResponse:
    """
    List approved contributor profiles (public endpoint).
    Returns ContributorPublic — condition_identity is never included.
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(ContributorProfile)
        .where(ContributorProfile.status == ContributorStatus.approved)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ContributorProfile)
        .where(ContributorProfile.status == ContributorStatus.approved)
        .order_by(ContributorProfile.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    profiles = result.scalars().all()

    return ContributorListResponse(
        items=[ContributorPublic.model_validate(p) for p in profiles],
        total=total,
    )


@router.get("/me", response_model=ContributorPrivate)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContributorPrivate:
    """
    Get the current contributor's own full profile.
    This is the ONLY endpoint that returns ContributorPrivate (which includes condition_identity).
    """
    result = await db.execute(
        select(ContributorProfile).where(
            ContributorProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor profile not found. Apply first.",
        )

    return ContributorPrivate.model_validate(profile)


@router.get("/{contributor_id}", response_model=ContributorPublic)
async def get_contributor(
    contributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContributorPublic:
    """
    Get a contributor's public profile.
    Returns ContributorPublic — condition_identity is never included, regardless of
    condition_identity_public. The frontend uses condition_identity_public as a signal
    to display a badge, but the raw value is not sent.
    """
    result = await db.execute(
        select(ContributorProfile).where(
            ContributorProfile.id == contributor_id,
            ContributorProfile.status == ContributorStatus.approved,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor profile not found.",
        )

    return ContributorPublic.model_validate(profile)


@router.post("/apply", response_model=ContributorPublic, status_code=status.HTTP_201_CREATED)
async def apply_as_contributor(
    body: ContributorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContributorPublic:
    """
    Apply to become a contributor. Creates a ContributorProfile with pending status.
    An editor/admin must approve the application.
    """
    existing = await db.execute(
        select(ContributorProfile).where(
            ContributorProfile.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied as a contributor.",
        )

    profile = ContributorProfile(
        user_id=current_user.id,
        bio=sanitize_html(body.bio),
        pronouns=sanitize_plain(body.pronouns),
        condition_identity=sanitize_plain(body.condition_identity),
        condition_identity_public=body.condition_identity_public,
        anonymous_mode=body.anonymous_mode,
        portfolio_url=body.portfolio_url,
        social_links=body.social_links,
        status=ContributorStatus.pending,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Contributor application: user_id={current_user.id}"
    )

    return ContributorPublic.model_validate(profile)


@router.patch("/me", response_model=ContributorPrivate)
async def update_my_profile(
    body: ContributorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContributorPrivate:
    """Update the current contributor's own profile."""
    result = await db.execute(
        select(ContributorProfile).where(
            ContributorProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor profile not found. Apply first.",
        )

    if body.bio is not None:
        profile.bio = sanitize_html(body.bio)
    if body.pronouns is not None:
        profile.pronouns = sanitize_plain(body.pronouns)
    if body.condition_identity is not None:
        profile.condition_identity = sanitize_plain(body.condition_identity)
    if body.condition_identity_public is not None:
        profile.condition_identity_public = body.condition_identity_public
    if body.anonymous_mode is not None:
        profile.anonymous_mode = body.anonymous_mode
    if body.portfolio_url is not None:
        profile.portfolio_url = body.portfolio_url
    if body.social_links is not None:
        profile.social_links = body.social_links

    await db.flush()
    await db.refresh(profile)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Contributor profile updated: user_id={current_user.id}"
    )

    return ContributorPrivate.model_validate(profile)
