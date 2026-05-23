import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.report import ReportContentType, ReportStatus


class ReportCreate(BaseModel):
    content_type: ReportContentType
    content_id: uuid.UUID
    reason: str


class ReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    admin_notes: Optional[str] = None


class ReportPublic(BaseModel):
    """Minimal report response for the submitter (no admin_notes)."""
    id: uuid.UUID
    content_type: ReportContentType
    content_id: uuid.UUID
    reason: str
    status: ReportStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportInternal(BaseModel):
    """Full report detail for admins, includes admin_notes."""
    id: uuid.UUID
    reporter_id: Optional[uuid.UUID] = None
    content_type: ReportContentType
    content_id: uuid.UUID
    reason: str
    status: ReportStatus
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportInternal]
    total: int
