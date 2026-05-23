import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.submission import SubmissionCategory, SubmissionStatus


class SubmissionCreate(BaseModel):
    title: str
    category: SubmissionCategory
    issue_id: Optional[uuid.UUID] = None
    body_text: str
    file_metadata: Optional[dict] = None
    content_warnings: Optional[list[str]] = None
    anonymous_byline: bool = False
    author_note: Optional[str] = None


class SubmissionUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[SubmissionCategory] = None
    issue_id: Optional[uuid.UUID] = None
    body_text: Optional[str] = None
    file_metadata: Optional[dict] = None
    content_warnings: Optional[list[str]] = None
    anonymous_byline: Optional[bool] = None
    author_note: Optional[str] = None


class SubmissionPublic(BaseModel):
    """Submission as seen by the contributor who owns it."""
    id: uuid.UUID
    contributor_id: uuid.UUID
    title: str
    category: SubmissionCategory
    issue_id: Optional[uuid.UUID] = None
    body_text: str
    file_metadata: Optional[dict] = None
    content_warnings: Optional[list[str]] = None
    anonymous_byline: bool
    author_note: Optional[str] = None
    status: SubmissionStatus
    assigned_editor_id: Optional[uuid.UUID] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubmissionInternal(BaseModel):
    """Full submission detail for editors/admins, includes all fields."""
    id: uuid.UUID
    contributor_id: uuid.UUID
    title: str
    category: SubmissionCategory
    issue_id: Optional[uuid.UUID] = None
    body_text: str
    file_metadata: Optional[dict] = None
    content_warnings: Optional[list[str]] = None
    anonymous_byline: bool
    author_note: Optional[str] = None
    status: SubmissionStatus
    assigned_editor_id: Optional[uuid.UUID] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatusUpdateRequest(BaseModel):
    status: SubmissionStatus


class AssignEditorRequest(BaseModel):
    editor_id: uuid.UUID


class SubmissionListResponse(BaseModel):
    items: list[SubmissionPublic]
    total: int


class EditorialSubmissionListResponse(BaseModel):
    items: list[SubmissionInternal]
    total: int
