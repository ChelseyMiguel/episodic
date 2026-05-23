"""
Resource management endpoints.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_editor
from app.models.resource import Resource, ResourceCategory, ResourceRegion
from app.models.user import User
from app.schemas.resource import (
    ResourceCreate,
    ResourceHideRequest,
    ResourceListResponse,
    ResourcePublic,
    ResourceUpdate,
)
from app.utils.sanitize import sanitize_html, sanitize_plain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    skip: int = 0,
    limit: int = 50,
    category: ResourceCategory | None = None,
    region: ResourceRegion | None = None,
    db: AsyncSession = Depends(get_db),
) -> ResourceListResponse:
    """List non-hidden resources with optional filters (public)."""
    query = select(Resource).where(Resource.is_hidden.is_(False))
    count_query = select(func.count()).select_from(Resource).where(Resource.is_hidden.is_(False))

    if category:
        query = query.where(Resource.category == category)
        count_query = count_query.where(Resource.category == category)
    if region:
        query = query.where(Resource.region == region)
        count_query = count_query.where(Resource.region == region)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Resource.created_at.desc()).offset(skip).limit(limit)
    )
    resources = result.scalars().all()

    return ResourceListResponse(
        items=[ResourcePublic.model_validate(r) for r in resources],
        total=total,
    )


@router.get("/{resource_id}", response_model=ResourcePublic)
async def get_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResourcePublic:
    """Get a resource by ID (public)."""
    result = await db.execute(
        select(Resource).where(
            Resource.id == resource_id, Resource.is_hidden.is_(False)
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )

    return ResourcePublic.model_validate(resource)


@router.post("", response_model=ResourcePublic, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResourcePublic:
    """Create a resource (editor+ only)."""
    assert_editor(current_user)

    resource = Resource(
        title=sanitize_plain(body.title),
        description=sanitize_html(body.description),
        category=body.category,
        external_link=body.external_link,
        region=body.region,
        reviewed_by_editor=body.reviewed_by_editor,
        last_reviewed_at=body.last_reviewed_at,
        is_hidden=False,
        created_by=current_user.id,
    )
    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Resource created: id={resource.id} by={current_user.id}"
    )

    return ResourcePublic.model_validate(resource)


@router.patch("/{resource_id}", response_model=ResourcePublic)
async def update_resource(
    resource_id: uuid.UUID,
    body: ResourceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResourcePublic:
    """Update a resource (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )

    if body.title is not None:
        resource.title = sanitize_plain(body.title)
    if body.description is not None:
        resource.description = sanitize_html(body.description)
    if body.category is not None:
        resource.category = body.category
    if body.external_link is not None:
        resource.external_link = body.external_link
    if body.region is not None:
        resource.region = body.region
    if body.reviewed_by_editor is not None:
        resource.reviewed_by_editor = body.reviewed_by_editor
    if body.last_reviewed_at is not None:
        resource.last_reviewed_at = body.last_reviewed_at

    await db.flush()
    await db.refresh(resource)

    return ResourcePublic.model_validate(resource)


@router.patch("/{resource_id}/hide", response_model=ResourcePublic)
async def hide_resource(
    resource_id: uuid.UUID,
    body: ResourceHideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResourcePublic:
    """Hide or unhide a resource (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )

    resource.is_hidden = body.is_hidden
    await db.flush()
    await db.refresh(resource)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Resource hidden={body.is_hidden}: id={resource_id} by={current_user.id}"
    )

    return ResourcePublic.model_validate(resource)
