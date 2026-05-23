import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Token sent in confirmation email; cleared after confirmation
    confirmation_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    unsubscribed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_active(self) -> bool:
        return self.is_confirmed and self.unsubscribed_at is None

    def __repr__(self) -> str:
        return f"<NewsletterSubscriber id={self.id} email={self.email}>"
