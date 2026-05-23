import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.issue import IssueStatus


class IssueCreate(BaseModel):
    title: str
    theme_description: str
    editors_letter: Optional[str] = None
    cover_image_metadata: Optional[dict] = None
    submission_deadline: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    status: IssueStatus = IssueStatus.planned


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    theme_description: Optional[str] = None
    editors_letter: Optional[str] = None
    cover_image_metadata: Optional[dict] = None
    submission_deadline: Optional[datetime] = None
    publication_date: Optional[datetime] = None


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssuePublic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    theme_description: str
    editors_letter: Optional[str] = None
    cover_image_metadata: Optional[dict] = None
    submission_deadline: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    status: IssueStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    items: list[IssuePublic]
    total: int
