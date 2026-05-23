import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class SubmissionCategory(str, Enum):
    essay = "essay"
    poetry = "poetry"
    visual_art = "visual_art"
    interview = "interview"
    resource = "resource"
    op_ed = "op_ed"
    other = "other"


class SubmissionStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    revision_requested = "revision_requested"
    rejected = "rejected"
    published = "published"


# Valid status transitions enforced in the editorial service layer
ALLOWED_TRANSITIONS: dict[SubmissionStatus, list[SubmissionStatus]] = {
    SubmissionStatus.draft: [SubmissionStatus.submitted],
    SubmissionStatus.submitted: [SubmissionStatus.under_review],
    SubmissionStatus.under_review: [
        SubmissionStatus.revision_requested,
        SubmissionStatus.accepted,
        SubmissionStatus.rejected,
    ],
    SubmissionStatus.revision_requested: [SubmissionStatus.submitted],
    SubmissionStatus.accepted: [SubmissionStatus.published],
    SubmissionStatus.rejected: [],
    SubmissionStatus.published: [],
}


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[SubmissionCategory] = mapped_column(
        SAEnum(SubmissionCategory, name="submissioncategory", native_enum=False), nullable=False
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
    )
    body_text: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON: {filename, size, mime_type, storage_key}
    file_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # JSON array of content warning strings
    content_warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    anonymous_byline: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    author_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus, name="submissionstatus", native_enum=False),
        nullable=False,
        default=SubmissionStatus.draft,
    )

    assigned_editor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    contributor: Mapped["User"] = relationship(
        "User", back_populates="submissions", foreign_keys=[contributor_id]
    )
    assigned_editor: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_submissions", foreign_keys=[assigned_editor_id]
    )
    issue: Mapped["Issue | None"] = relationship("Issue", back_populates="submissions")
    editorial_notes: Mapped[list["EditorialNote"]] = relationship(
        "EditorialNote", back_populates="submission", cascade="all, delete-orphan"
    )
    article: Mapped["Article | None"] = relationship(
        "Article", back_populates="submission", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Submission id={self.id} title={self.title} status={self.status}>"


class EditorialNote(Base):
    """
    Private editorial notes on a submission.
    IMPORTANT: These notes are NEVER exposed to contributors or the public.
    Only editors and admins can create and view them.
    """

    __tablename__ = "editorial_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    editor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission", back_populates="editorial_notes"
    )
    editor: Mapped["User"] = relationship("User", back_populates="editorial_notes")

    def __repr__(self) -> str:
        return f"<EditorialNote id={self.id} submission_id={self.submission_id}>"
