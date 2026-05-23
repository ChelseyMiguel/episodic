import uuid
from enum import Enum

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class UserRole(str, Enum):
    reader = "reader"
    contributor = "contributor"
    editor = "editor"
    admin = "admin"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", native_enum=False), nullable=False, default=UserRole.reader
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    contributor_profile: Mapped["ContributorProfile"] = relationship(
        "ContributorProfile", back_populates="user", uselist=False
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="contributor",
        foreign_keys="Submission.contributor_id",
    )
    assigned_submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="assigned_editor",
        foreign_keys="Submission.assigned_editor_id",
    )
    editorial_notes: Mapped[list["EditorialNote"]] = relationship(
        "EditorialNote", back_populates="editor"
    )
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="contributor"
    )
    resources: Mapped[list["Resource"]] = relationship(
        "Resource", back_populates="created_by_user"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="reporter"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
