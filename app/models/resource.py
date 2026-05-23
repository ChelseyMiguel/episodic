import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import String, Text, Boolean, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ResourceCategory(str, Enum):
    school_accessibility = "school_accessibility"
    medical_advocacy = "medical_advocacy"
    mental_health = "mental_health"
    disability_rights = "disability_rights"
    chronic_illness = "chronic_illness"
    emergency_support = "emergency_support"
    other = "other"


class ResourceRegion(str, Enum):
    global_ = "global"
    US = "US"
    Hawaii = "Hawaii"
    other = "other"


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ResourceCategory] = mapped_column(
        SAEnum(ResourceCategory, name="resourcecategory", native_enum=False), nullable=False
    )
    external_link: Mapped[str] = mapped_column(String(1000), nullable=False)
    region: Mapped[ResourceRegion] = mapped_column(
        SAEnum(ResourceRegion, name="resourceregion", native_enum=False),
        nullable=False,
        default=ResourceRegion.global_,
    )
    reviewed_by_editor: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_reviewed_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Hidden resources are not shown publicly (moderation/takedown mechanism)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    created_by_user: Mapped["User | None"] = relationship(
        "User", back_populates="resources"
    )

    def __repr__(self) -> str:
        return f"<Resource id={self.id} title={self.title}>"
