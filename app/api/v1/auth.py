"""
Authentication endpoints.

Rate limits:
- POST /auth/login: 5 requests/minute (brute force protection)
- POST /auth/signup: 10 requests/minute (spam protection)
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import (
    block_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_token_blocked,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic
from app.services.email import send_welcome_email

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new account. Returns JWT access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name.strip(),
        role=UserRole.reader,
        is_active=True,
        is_email_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    jti = str(uuid.uuid4())
    access_token = create_access_token({"sub": str(user.id), "jti": jti})
    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user.id), "jti": refresh_jti})

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] New user signup: id={user.id} email={user.email}"
    )

    await send_welcome_email(user.email, user.display_name)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and receive JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning(
            f"[{datetime.now(timezone.utc).isoformat()}] Failed login attempt for email={body.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    jti = str(uuid.uuid4())
    access_token = create_access_token({"sub": str(user.id), "jti": jti})
    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user.id), "jti": refresh_jti})

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] User login: id={user.id} role={user.role}"
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Logout by providing the refresh token to block.
    Note: Access tokens are short-lived (30 min). In production, also accept the
    access token's JTI here and block it. With httpOnly cookies, the server clears both.
    """
    try:
        payload = decode_token(body.refresh_token)
        jti = payload.get("jti")
        if jti:
            block_token(jti)
    except JWTError:
        pass  # Even if token is invalid, logout succeeds

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] User logout: id={current_user.id}"
    )
    return MessageResponse(message="Successfully logged out.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception

        jti = payload.get("jti")
        if jti and is_token_blocked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been invalidated.",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    # Block old refresh token (rotation)
    if jti:
        block_token(jti)

    new_jti = str(uuid.uuid4())
    access_token = create_access_token({"sub": str(user.id), "jti": new_jti})
    new_refresh_jti = str(uuid.uuid4())
    refresh = create_refresh_token({"sub": str(user.id), "jti": new_refresh_jti})

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Token refreshed: id={user.id}"
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh)


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """Get the currently authenticated user's profile."""
    return UserPublic.model_validate(current_user)
