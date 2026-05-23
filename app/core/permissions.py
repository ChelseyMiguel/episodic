"""
Role-based permission checks for Episodic.

Role hierarchy (lowest to highest privilege):
  reader < contributor < editor < admin

Editors can do everything contributors can.
Admins can do everything editors can, plus user management.
"""
from fastapi import HTTPException, status

from app.models.user import User, UserRole


ROLE_LEVELS: dict[UserRole, int] = {
    UserRole.reader: 0,
    UserRole.contributor: 1,
    UserRole.editor: 2,
    UserRole.admin: 3,
}


def require_role(user: User, minimum_role: UserRole) -> None:
    """
    Raises HTTP 403 if the user's role is below the minimum required role.
    Also raises 403 if the user account is inactive.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    if ROLE_LEVELS.get(user.role, 0) < ROLE_LEVELS.get(minimum_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires '{minimum_role.value}' role or higher.",
        )


def is_editor_or_above(user: User) -> bool:
    return ROLE_LEVELS.get(user.role, 0) >= ROLE_LEVELS[UserRole.editor]


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def is_contributor_or_above(user: User) -> bool:
    return ROLE_LEVELS.get(user.role, 0) >= ROLE_LEVELS[UserRole.contributor]


def assert_editor(user: User) -> None:
    require_role(user, UserRole.editor)


def assert_admin(user: User) -> None:
    require_role(user, UserRole.admin)


def assert_contributor(user: User) -> None:
    require_role(user, UserRole.contributor)
