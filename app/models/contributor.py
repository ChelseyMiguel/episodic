"""
ContributorProfile model.

PRIVACY DESIGN:
- condition_identity is a sensitive field containing the contributor's chronic illness
  or disability identity. It MUST NEVER be exposed in any public API response.
  It is only surfaced in the /contributors/me endpoint (own profile, authenticated).
- condition_identity_public: when True, the contributor has explicitly opted in to
  sharing their condition identity on their public profile. Even then, exposure is
  controlled at the schema/serialization layer, not here.
- anonymous_mode: if True, submissions by this contributor default to anonymous bylines.
"""
import uuid
from enum import Enum

from sqlalchemy import String, Boolean, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ContributorStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    suspended = "suspended"


class ContributorProfile(Base, TimestampMixin):
    __tablename__ = "contributor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # PRIVATE: This field contains the contributor's personal chronic illness /
    # disability identity. It MUST NEVER appear in any public Pydantic response schema.
    # Access is restricted to the /contributors/me endpoint only.
    condition_identity: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When True, the contributor has explicitly opted in to showing their
    # condition_identity on their public profile page. The schema layer enforces this.
    condition_identity_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # When True, all submissions by this contributor default to an anonymous byline.
    anonymous_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # JSON: {twitter, instagram, website, etc.}
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[ContributorStatus] = mapped_column(
        SAEnum(ContributorStatus, name="contributorstatus", native_enum=False),
        nullable=False,
        default=ContributorStatus.pending,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contributor_profile")

    def __repr__(self) -> str:
        return f"<ContributorProfile id={self.id} user_id={self.user_id} status={self.status}>"
