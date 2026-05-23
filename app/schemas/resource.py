import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator

from app.models.resource import ResourceCategory, ResourceRegion


class ResourceCreate(BaseModel):
    title: str
    description: str
    category: ResourceCategory
    external_link: str
    region: ResourceRegion = ResourceRegion.global_
    reviewed_by_editor: bool = False
    last_reviewed_at: Optional[date] = None


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ResourceCategory] = None
    external_link: Optional[str] = None
    region: Optional[ResourceRegion] = None
    reviewed_by_editor: Optional[bool] = None
    last_reviewed_at: Optional[date] = None


class ResourcePublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: ResourceCategory
    external_link: str
    region: ResourceRegion
    reviewed_by_editor: bool
    last_reviewed_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResourceHideRequest(BaseModel):
    is_hidden: bool


class ResourceListResponse(BaseModel):
    items: list[ResourcePublic]
    total: int
