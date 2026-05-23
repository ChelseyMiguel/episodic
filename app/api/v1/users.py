"""
User management endpoints — admin only.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_admin
from app.models.user import User
from app.schemas.user import UserListResponse, UserPublic, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List all users (admin only)."""
    assert_admin(current_user)

    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return UserListResponse(
        items=[UserPublic.model_validate(u) for u in users],
        total=total,
    )


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """Get a user by ID (admin only)."""
    assert_admin(current_user)

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserPublic.model_validate(user)


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """Update a user's role or active status (admin only)."""
    assert_admin(current_user)

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.display_name is not None:
        user.display_name = body.display_name.strip()

    await db.flush()
    await db.refresh(user)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Admin {current_user.id} updated user {user_id}"
    )

    return UserPublic.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a user (admin only)."""
    assert_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account.",
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.flush()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Admin {current_user.id} soft-deleted user {user_id}"
    )
