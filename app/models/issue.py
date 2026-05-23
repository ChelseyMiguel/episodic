import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class IssueStatus(str, Enum):
    planned = "planned"
    open_for_submissions = "open_for_submissions"
    editing = "editing"
    published = "published"
    archived = "archived"


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    theme_description: Mapped[str] = mapped_column(Text, nullable=False)
    editors_letter: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON: {storage_key, alt_text, caption}
    cover_image_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    submission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus, name="issuestatus", native_enum=False),
        nullable=False,
        default=IssueStatus.planned,
    )

    # Relationships
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="issue"
    )
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="issue"
    )

    def __repr__(self) -> str:
        return f"<Issue id={self.id} title={self.title} status={self.status}>"
