"""
Newsletter subscription endpoints.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_admin
from app.models.newsletter import NewsletterSubscriber
from app.models.user import User
from app.schemas.newsletter import (
    MessageResponse,
    SubscribeRequest,
    SubscriberListResponse,
    SubscriberPublic,
    UnsubscribeRequest,
)
from app.services.email import send_newsletter_confirmation_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/newsletter", tags=["Newsletter"])


@router.post("/subscribe", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Subscribe an email to the newsletter."""
    result = await db.execute(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.email == body.email
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.unsubscribed_at is not None:
            # Re-subscribe
            existing.unsubscribed_at = None
            existing.is_confirmed = False
            existing.confirmation_token = str(uuid.uuid4())
            await db.flush()
            await send_newsletter_confirmation_email(
                existing.email, existing.confirmation_token
            )
            return MessageResponse(
                message="Welcome back! Please check your email to confirm your subscription."
            )
        return MessageResponse(
            message="This email is already subscribed."
        )

    token = str(uuid.uuid4())
    subscriber = NewsletterSubscriber(
        email=body.email,
        is_confirmed=False,
        confirmation_token=token,
        subscribed_at=datetime.now(timezone.utc),
    )
    db.add(subscriber)
    await db.flush()

    await send_newsletter_confirmation_email(body.email, token)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Newsletter subscription: email={body.email}"
    )

    return MessageResponse(
        message="Subscription received. Please check your email to confirm."
    )


@router.get("/confirm", response_model=MessageResponse)
async def confirm_subscription(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Confirm a newsletter subscription via the token sent in the confirmation email.
    Clears the token after use so it cannot be replayed.
    """
    result = await db.execute(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.confirmation_token == token
        )
    )
    subscriber = result.scalar_one_or_none()

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired confirmation token.",
        )

    if subscriber.is_confirmed:
        return MessageResponse(message="Your subscription is already confirmed.")

    subscriber.is_confirmed = True
    subscriber.confirmation_token = None  # one-time use — clear after confirmation
    await db.flush()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Newsletter confirmed: email={subscriber.email}"
    )

    return MessageResponse(message="Subscription confirmed. Welcome to Episodic!")


@router.get("/unsubscribe", response_model=MessageResponse)
async def unsubscribe_via_link(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    One-click unsubscribe from a link in an email.
    Uses the subscriber's UUID as the token — safe because unsubscribing is a benign action.
    Include this URL in every outgoing email to comply with CAN-SPAM / GDPR.
    Example link: https://api.episodic.org/api/v1/newsletter/unsubscribe?token=<subscriber_id>
    """
    try:
        subscriber_id = uuid.UUID(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid unsubscribe token.",
        )

    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.id == subscriber_id)
    )
    subscriber = result.scalar_one_or_none()

    if not subscriber or subscriber.unsubscribed_at is not None:
        return MessageResponse(message="Already unsubscribed or not found.")

    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Newsletter unsubscribe via link: email={subscriber.email}"
    )

    return MessageResponse(message="You've been unsubscribed. Sorry to see you go.")


@router.post("/unsubscribe", response_model=MessageResponse)
async def unsubscribe(
    body: UnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Unsubscribe an email from the newsletter."""
    result = await db.execute(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.email == body.email
        )
    )
    subscriber = result.scalar_one_or_none()

    if not subscriber or subscriber.unsubscribed_at is not None:
        return MessageResponse(message="Email not found in subscriber list.")

    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Newsletter unsubscribe: email={body.email}"
    )

    return MessageResponse(message="Successfully unsubscribed.")


@router.get("/subscribers", response_model=SubscriberListResponse)
async def list_subscribers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriberListResponse:
    """List all newsletter subscribers (admin only)."""
    assert_admin(current_user)

    count_result = await db.execute(select(func.count()).select_from(NewsletterSubscriber))
    total = count_result.scalar_one()

    result = await db.execute(
        select(NewsletterSubscriber)
        .order_by(NewsletterSubscriber.subscribed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    subscribers = result.scalars().all()

    return SubscriberListResponse(
        items=[SubscriberPublic.model_validate(s) for s in subscribers],
        total=total,
    )
