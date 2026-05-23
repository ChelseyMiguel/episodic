import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.submission import SubmissionStatus


class EditorialNoteCreate(BaseModel):
    note: str


class EditorialNotePublic(BaseModel):
    """Editorial notes — only visible to editors and admins, never to contributors."""
    id: uuid.UUID
    submission_id: uuid.UUID
    editor_id: uuid.UUID
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EditorialNoteListResponse(BaseModel):
    items: list[EditorialNotePublic]
    total: int
