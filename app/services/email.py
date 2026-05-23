"""
Email service for Episodic.

Uses SendGrid for transactional email. If SENDGRID_API_KEY is not set
(e.g. local development), all sends fall back to console logging so the
app works without credentials.

Design rules:
- Email failures NEVER raise exceptions to callers — a failed email must
  not roll back a database transaction or return a 500 to the user.
- Every outgoing email includes an unsubscribe link (CAN-SPAM / GDPR).
- SendGrid's client is synchronous, so we run it in a thread pool via
  asyncio.to_thread to avoid blocking the event loop.
"""
import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _unsubscribe_url(subscriber_id: Optional[str] = None) -> str:
    """
    Build a one-click unsubscribe URL for email footers.
    subscriber_id is the NewsletterSubscriber UUID; pass None for
    transactional emails where no subscriber record exists.
    """
    if subscriber_id:
        return f"{settings.APP_BASE_URL}/api/v1/newsletter/unsubscribe?token={subscriber_id}"
    return f"{settings.APP_BASE_URL}/api/v1/newsletter/unsubscribe"


def _wrap_html(subject: str, body_html: str, subscriber_id: Optional[str] = None) -> str:
    """Wrap email body in a minimal, readable HTML shell."""
    unsubscribe = _unsubscribe_url(subscriber_id)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
  <style>
    body {{ font-family: Georgia, serif; background: #fafaf8; margin: 0; padding: 0; }}
    .container {{ max-width: 560px; margin: 40px auto; background: #fff;
                  border: 1px solid #e8e4df; border-radius: 4px; padding: 40px; }}
    h1 {{ font-size: 22px; color: #1a1a1a; margin-top: 0; }}
    p {{ font-size: 16px; line-height: 1.6; color: #333; }}
    a {{ color: #7c4dff; }}
    .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e8e4df;
               font-size: 12px; color: #999; }}
    .wordmark {{ font-size: 13px; letter-spacing: 0.08em; color: #555; margin-bottom: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <p class="wordmark">EPISODIC</p>
    {body_html}
    <div class="footer">
      <p>
        You're receiving this because you have an account with
        <a href="{settings.APP_BASE_URL}">Episodic</a>.<br />
        <a href="{unsubscribe}">Unsubscribe</a> from non-essential emails.
      </p>
    </div>
  </div>
</body>
</html>"""


def _send_via_sendgrid(to_email: str, subject: str, html: str) -> None:
    """Synchronous SendGrid send — called inside asyncio.to_thread."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    logger.info(f"Email sent via SendGrid: to={to_email} subject='{subject}' status={response.status_code}")


async def _send(to_email: str, subject: str, html: str) -> None:
    """
    Send an email. Falls back to console logging if no API key is configured.
    Never raises — catches and logs all exceptions.
    """
    if not settings.SENDGRID_API_KEY:
        logger.info(
            f"[EMAIL DEV] to={to_email} | subject='{subject}'\n"
            f"(Set SENDGRID_API_KEY to send real emails)"
        )
        return

    try:
        await asyncio.to_thread(_send_via_sendgrid, to_email, subject, html)
    except Exception as e:
        # Email failure must not affect the caller's response or transaction.
        logger.error(f"Email send failed: to={to_email} subject='{subject}' error={e}")


# ---------------------------------------------------------------------------
# Public email functions — called by route handlers
# ---------------------------------------------------------------------------

async def send_welcome_email(to_email: str, display_name: str) -> None:
    """Sent immediately after a new user signs up."""
    subject = "Welcome to Episodic"
    body = f"""
      <h1>Welcome, {display_name}.</h1>
      <p>
        We're glad you're here. Episodic is a space for young people living with
        chronic illness and disability — your stories, your art, your advocacy.
      </p>
      <p>
        If you'd like to contribute, you can apply for a contributor profile
        from your account settings. We review applications on a rolling basis.
      </p>
      <p>— The Episodic Team</p>
    """
    await _send(to_email, subject, _wrap_html(subject, body))


async def send_submission_received_email(to_email: str, submission_title: str) -> None:
    """Sent when a contributor formally submits a piece (draft → submitted)."""
    subject = f"We received your submission: {submission_title}"
    body = f"""
      <h1>We got it.</h1>
      <p>
        Your submission <strong>"{submission_title}"</strong> is now in our editorial queue.
        We'll be in touch once an editor has had a chance to review it.
      </p>
      <p>
        You can check the status of your submission at any time from your contributor dashboard.
      </p>
      <p>Thank you for trusting us with your work.</p>
      <p>— The Episodic Editorial Team</p>
    """
    await _send(to_email, subject, _wrap_html(subject, body))


# Status-specific subjects and messages — intentional variation in tone.
_STATUS_COPY: dict[str, tuple[str, str]] = {
    "under_review": (
        "Your submission is under review",
        "<h1>Under review.</h1><p>An editor has picked up your submission and is reading it now. We'll update you soon.</p>",
    ),
    "revision_requested": (
        "Revision requested for your submission",
        "<h1>A note from our editors.</h1><p>We've read your piece and have some thoughts. Please log in to your dashboard to see the editorial notes and resubmit when you're ready. There's no deadline — take the time you need.</p>",
    ),
    "accepted": (
        "Your piece has been accepted — congratulations",
        "<h1>We'd love to publish your work.</h1><p>Your submission has been accepted by our editorial team. We'll be in touch about next steps, including publication timing and any final edits.</p>",
    ),
    "rejected": (
        "A note on your submission",
        "<h1>Thank you for submitting.</h1><p>After careful consideration, we aren't able to publish this piece in the current cycle. This is never an easy note to send — your work matters, and we're grateful you shared it with us. We welcome future submissions.</p>",
    ),
    "published": (
        "Your work is live on Episodic",
        "<h1>You're published.</h1><p>Your piece is now live on Episodic. Thank you for sharing your story with our community.</p>",
    ),
}


async def send_submission_status_email(
    to_email: str, submission_title: str, new_status: str
) -> None:
    """Sent whenever an editor changes the status of a submission."""
    subject_template, body_template = _STATUS_COPY.get(
        new_status,
        (
            f"Update on your submission: {submission_title}",
            f"<h1>Submission update.</h1><p>The status of <strong>\"{submission_title}\"</strong> has been updated to <strong>{new_status}</strong>. Log in to your dashboard for details.</p>",
        ),
    )
    # Append title to subject for clarity in crowded inboxes
    subject = f"{subject_template}: {submission_title}"
    body = body_template + f"""
      <p style="margin-top:24px;">
        <a href="{settings.APP_BASE_URL}/dashboard">View your dashboard →</a>
      </p>
      <p>— The Episodic Editorial Team</p>
    """
    await _send(to_email, subject, _wrap_html(subject, body))


async def send_newsletter_confirmation_email(
    to_email: str, confirmation_token: str
) -> None:
    """Double opt-in confirmation for newsletter subscribers."""
    confirm_url = f"{settings.APP_BASE_URL}/api/v1/newsletter/confirm?token={confirmation_token}"
    subject = "Confirm your Episodic newsletter subscription"
    body = f"""
      <h1>One quick step.</h1>
      <p>
        Click below to confirm your subscription to the Episodic newsletter.
        We send occasional updates about new issues, calls for submissions, and resources.
      </p>
      <p style="margin: 32px 0;">
        <a href="{confirm_url}"
           style="background:#1a1a1a; color:#fff; padding:12px 24px;
                  text-decoration:none; border-radius:3px; font-family:sans-serif;">
          Confirm subscription
        </a>
      </p>
      <p style="font-size:13px; color:#999;">
        Or copy this link: {confirm_url}
      </p>
      <p>If you didn't sign up, you can safely ignore this email.</p>
    """
    await _send(to_email, subject, _wrap_html(subject, body))


async def send_contributor_approved_email(to_email: str, display_name: str) -> None:
    """Sent when an admin approves a contributor application."""
    subject = "Your Episodic contributor application was approved"
    body = f"""
      <h1>You're in, {display_name}.</h1>
      <p>
        Your contributor application has been approved. You can now submit work
        through your dashboard.
      </p>
      <p>
        We accept essays, poetry, visual art, interviews, resource guides, and more.
        Check our current open calls for themed issues from the submissions page.
      </p>
      <p>
        <a href="{settings.APP_BASE_URL}/dashboard">Go to your dashboard →</a>
      </p>
      <p>We can't wait to read your work.</p>
      <p>— The Episodic Team</p>
    """
    await _send(to_email, subject, _wrap_html(subject, body))
