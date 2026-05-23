import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ReportContentType(str, Enum):
    article = "article"
    resource = "resource"
    comment = "comment"


class ReportStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Optional: can be None for anonymous reports
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    content_type: Mapped[ReportContentType] = mapped_column(
        SAEnum(ReportContentType, name="reportcontenttype", native_enum=False), nullable=False
    )

    # Polymorphic UUID reference — points to the reported content item
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus, name="reportstatus", native_enum=False),
        nullable=False,
        default=ReportStatus.pending,
    )

    # PRIVATE: Only visible to admins
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    reporter: Mapped["User | None"] = relationship("User", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} content_type={self.content_type} status={self.status}>"
