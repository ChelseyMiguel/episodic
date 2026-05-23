import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class SubscribeRequest(BaseModel):
    email: EmailStr


class UnsubscribeRequest(BaseModel):
    email: EmailStr


class SubscriberPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_confirmed: bool
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubscriberListResponse(BaseModel):
    items: list[SubscriberPublic]
    total: int


class MessageResponse(BaseModel):
    message: str
