"""
Contributor profile schemas.

PRIVACY DESIGN:
- ContributorPublic: The schema used in all public-facing API responses.
  It NEVER includes condition_identity, regardless of condition_identity_public.
  The condition_identity_public flag is evaluated at the endpoint level:
  if True, a separate "condition_identity_display" field (derived, not raw) MAY be shown.
  This keeps the raw personal data field completely out of the serialization path.

- ContributorPrivate: Used ONLY for /contributors/me (own profile).
  Includes condition_identity so the contributor can see and edit their own data.
  This schema must NEVER be used in any other endpoint.

- anonymous_mode is included in ContributorPublic as it's relevant for readers
  understanding how contributions are attributed, but condition_identity is not.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator

from app.models.contributor import ContributorStatus


class ContributorCreate(BaseModel):
    bio: Optional[str] = None
    pronouns: Optional[str] = None
    # PRIVATE: stored but never returned in public schemas
    condition_identity: Optional[str] = None
    condition_identity_public: bool = False
    anonymous_mode: bool = False
    portfolio_url: Optional[str] = None
    social_links: Optional[dict] = None


class ContributorUpdate(BaseModel):
    bio: Optional[str] = None
    pronouns: Optional[str] = None
    # PRIVATE: contributor can update their own condition identity
    condition_identity: Optional[str] = None
    condition_identity_public: Optional[bool] = None
    anonymous_mode: Optional[bool] = None
    portfolio_url: Optional[str] = None
    social_links: Optional[dict] = None


class ContributorPublic(BaseModel):
    """
    Public-facing contributor profile schema.
    CRITICAL: condition_identity is intentionally EXCLUDED from this schema.
    Even if condition_identity_public=True, the raw field is never serialized here.
    The display logic (whether to show a user-friendly version) lives in the endpoint.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    bio: Optional[str] = None
    pronouns: Optional[str] = None
    # NOTE: condition_identity is NOT here — this is intentional privacy protection.
    # condition_identity_public is included so the frontend knows whether to show
    # a "shares condition identity" badge, but the actual value is not exposed.
    condition_identity_public: bool
    anonymous_mode: bool
    portfolio_url: Optional[str] = None
    social_links: Optional[dict] = None
    status: ContributorStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ContributorPrivate(BaseModel):
    """
    Full contributor profile schema — for the contributor's own /me endpoint ONLY.
    Includes condition_identity which is a sensitive personal field.
    This schema MUST NOT be used in any public or editor-facing endpoint.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    bio: Optional[str] = None
    pronouns: Optional[str] = None
    # PRIVATE field — only visible to the contributor themselves
    condition_identity: Optional[str] = None
    condition_identity_public: bool
    anonymous_mode: bool
    portfolio_url: Optional[str] = None
    social_links: Optional[dict] = None
    status: ContributorStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContributorStatusUpdate(BaseModel):
    status: ContributorStatus


class ContributorListResponse(BaseModel):
    items: list[ContributorPublic]
    total: int
