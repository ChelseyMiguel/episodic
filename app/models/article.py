import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Table, Column, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ArticleStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"
    archived = "archived"


# Association table for many-to-many Article <-> Tag
article_tags = Table(
    "article_tags",
    Base.metadata,
    Column(
        "article_id",
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Relationships
    articles: Mapped[list["Article"]] = relationship(
        "Article", secondary=article_tags, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name}>"


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, index=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    contributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When True, show "Anonymous" or byline_name instead of contributor's display_name.
    # This is CRITICAL for contributor privacy — never override this in serialization.
    anonymous_byline: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Optional override for the displayed author name (e.g., a chosen pseudonym).
    # Only used when anonymous_byline is True.
    byline_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
    )

    # JSON array of content warning strings
    content_warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    status: Mapped[ArticleStatus] = mapped_column(
        SAEnum(ArticleStatus, name="articlestatus", native_enum=False),
        nullable=False,
        default=ArticleStatus.draft,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    submission: Mapped["Submission | None"] = relationship(
        "Submission", back_populates="article"
    )
    contributor: Mapped["User"] = relationship("User", back_populates="articles")
    issue: Mapped["Issue | None"] = relationship("Issue", back_populates="articles")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=article_tags, back_populates="articles"
    )

    @property
    def effective_byline(self) -> str:
        """
        Returns the display byline for this article.
        Respects anonymous_byline flag — never exposes real name when anonymous.
        """
        if self.anonymous_byline:
            return self.byline_name or "Anonymous"
        return self.contributor.display_name if self.contributor else "Unknown"

    def __repr__(self) -> str:
        return f"<Article id={self.id} slug={self.slug} status={self.status}>"
