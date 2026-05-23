"""
Base mixins for common model fields.
TimestampMixin adds created_at/updated_at.
SoftDeleteMixin adds deleted_at for soft deletes (row is never removed, just hidden).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at and updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Adds deleted_at column for soft deletes.
    Records are never physically removed — instead deleted_at is set.
    All queries should filter WHERE deleted_at IS NULL unless specifically reviewing deleted records.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
