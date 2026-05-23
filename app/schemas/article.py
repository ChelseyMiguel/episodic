import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.article import ArticleStatus
from app.models.submission import SubmissionCategory


class TagSchema(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class ArticleCreate(BaseModel):
    title: str
    body: str
    category: SubmissionCategory
    contributor_id: uuid.UUID
    anonymous_byline: bool = False
    byline_name: Optional[str] = None
    issue_id: Optional[uuid.UUID] = None
    excerpt: Optional[str] = None
    content_warnings: Optional[list[str]] = None
    tag_ids: Optional[list[uuid.UUID]] = None
    status: ArticleStatus = ArticleStatus.draft
    scheduled_for: Optional[datetime] = None
    featured: bool = False


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[SubmissionCategory] = None
    anonymous_byline: Optional[bool] = None
    byline_name: Optional[str] = None
    issue_id: Optional[uuid.UUID] = None
    content_warnings: Optional[list[str]] = None
    tag_ids: Optional[list[uuid.UUID]] = None
    status: Optional[ArticleStatus] = None
    scheduled_for: Optional[datetime] = None
    featured: Optional[bool] = None


class ArticlePublic(BaseModel):
    """
    Public article response.
    IMPORTANT: byline is derived — never exposes contributor's real name
    when anonymous_byline=True. The byline field shows "Anonymous" or byline_name.
    """
    id: uuid.UUID
    title: str
    slug: str
    excerpt: Optional[str] = None
    body: str
    category: str
    # Derived byline — safe to expose publicly
    byline: str
    anonymous_byline: bool
    issue_id: Optional[uuid.UUID] = None
    content_warnings: Optional[list[str]] = None
    status: ArticleStatus
    published_at: Optional[datetime] = None
    featured: bool
    tags: list[TagSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleInternal(BaseModel):
    """Full article detail for editors/admins."""
    id: uuid.UUID
    submission_id: Optional[uuid.UUID] = None
    title: str
    slug: str
    excerpt: Optional[str] = None
    body: str
    category: str
    contributor_id: uuid.UUID
    byline: str
    anonymous_byline: bool
    byline_name: Optional[str] = None
    issue_id: Optional[uuid.UUID] = None
    content_warnings: Optional[list[str]] = None
    status: ArticleStatus
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    featured: bool
    tags: list[TagSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: list[ArticlePublic]
    total: int


class FeatureToggleRequest(BaseModel):
    featured: bool
