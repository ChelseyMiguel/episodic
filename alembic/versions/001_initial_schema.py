"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE userrole AS ENUM ('reader', 'contributor', 'editor', 'admin')")
    op.execute("CREATE TYPE contributorstatus AS ENUM ('pending', 'approved', 'suspended')")
    op.execute("CREATE TYPE submissioncategory AS ENUM ('essay', 'poetry', 'visual_art', 'interview', 'resource', 'op_ed', 'other')")
    op.execute("CREATE TYPE submissionstatus AS ENUM ('draft', 'submitted', 'under_review', 'accepted', 'revision_requested', 'rejected', 'published')")
    op.execute("CREATE TYPE articlestatus AS ENUM ('draft', 'scheduled', 'published', 'archived')")
    op.execute("CREATE TYPE issuestatus AS ENUM ('planned', 'open_for_submissions', 'editing', 'published', 'archived')")
    op.execute("CREATE TYPE resourcecategory AS ENUM ('school_accessibility', 'medical_advocacy', 'mental_health', 'disability_rights', 'chronic_illness', 'emergency_support', 'other')")
    op.execute("CREATE TYPE resourceregion AS ENUM ('global', 'US', 'Hawaii', 'other')")
    op.execute("CREATE TYPE reportcontenttype AS ENUM ('article', 'resource', 'comment')")
    op.execute("CREATE TYPE reportstatus AS ENUM ('pending', 'reviewed', 'resolved', 'dismissed')")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # issues (needed before submissions and articles)
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("theme_description", sa.Text(), nullable=False),
        sa.Column("editors_letter", sa.Text(), nullable=True),
        sa.Column("cover_image_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_issues_slug", "issues", ["slug"])

    # contributor_profiles
    op.create_table(
        "contributor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("pronouns", sa.String(50), nullable=True),
        sa.Column("condition_identity", sa.Text(), nullable=True),
        sa.Column("condition_identity_public", sa.Boolean(), nullable=False, default=False),
        sa.Column("anonymous_mode", sa.Boolean(), nullable=False, default=False),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("social_links", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contributor_profiles_user_id", "contributor_profiles", ["user_id"])

    # submissions
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("file_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("content_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("anonymous_byline", sa.Boolean(), nullable=False, default=False),
        sa.Column("author_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("assigned_editor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_submissions_contributor_id", "submissions", ["contributor_id"])

    # editorial_notes
    op.create_table(
        "editorial_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("editor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_editorial_notes_submission_id", "editorial_notes", ["submission_id"])

    # tags
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
    )
    op.create_index("ix_tags_slug", "tags", ["slug"])

    # articles
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(300), nullable=False, unique=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("contributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anonymous_byline", sa.Boolean(), nullable=False, default=False),
        sa.Column("byline_name", sa.String(100), nullable=True),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"])
    op.create_index("ix_articles_contributor_id", "articles", ["contributor_id"])

    # article_tags (association table)
    op.create_table(
        "article_tags",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # resources
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("external_link", sa.String(1000), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("reviewed_by_editor", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_reviewed_at", sa.Date(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # newsletter_subscribers
    op.create_table(
        "newsletter_subscribers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, default=False),
        sa.Column("confirmation_token", sa.String(255), nullable=True),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_newsletter_subscribers_email", "newsletter_subscribers", ["email"])


def downgrade() -> None:
    op.drop_table("newsletter_subscribers")
    op.drop_table("reports")
    op.drop_table("resources")
    op.drop_table("article_tags")
    op.drop_table("articles")
    op.drop_table("tags")
    op.drop_table("editorial_notes")
    op.drop_table("submissions")
    op.drop_table("contributor_profiles")
    op.drop_table("issues")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS reportcontenttype")
    op.execute("DROP TYPE IF EXISTS resourceregion")
    op.execute("DROP TYPE IF EXISTS resourcecategory")
    op.execute("DROP TYPE IF EXISTS issuestatus")
    op.execute("DROP TYPE IF EXISTS articlestatus")
    op.execute("DROP TYPE IF EXISTS submissionstatus")
    op.execute("DROP TYPE IF EXISTS submissioncategory")
    op.execute("DROP TYPE IF EXISTS contributorstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
