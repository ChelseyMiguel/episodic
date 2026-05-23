import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    display_name: Optional[str] = None


class UserListResponse(BaseModel):
    items: list[UserPublic]
    total: int
