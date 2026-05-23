"""
JWT authentication and password hashing utilities.

Token approach:
- Access token: 30 min expiry, returned in response body.
- Refresh token: 7 days expiry, returned in response body.
- In production, consider storing tokens in httpOnly cookies to prevent XSS access.
  The current approach (response body) is simpler for API clients and mobile apps.

Token blocklist:
- Uses an in-memory set for demonstration. In production, replace with Redis
  so the blocklist persists across restarts and scales horizontally.
  Example: redis_client.setex(jti, token_expiry_seconds, "blocked")
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory JWT blocklist — stores JTI (JWT ID) strings of invalidated tokens.
# PRODUCTION NOTE: Replace with Redis for persistence and horizontal scaling.
_token_blocklist: set[str] = set()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Access token created for sub={data.get('sub')}"
    )
    return token


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Refresh token created for sub={data.get('sub')}"
    )
    return token


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload


def block_token(jti: str) -> None:
    """Add a token's JTI to the blocklist (logout / invalidation)."""
    _token_blocklist.add(jti)
    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Token blocked: jti={jti}"
    )


def is_token_blocked(jti: str) -> bool:
    return jti in _token_blocklist
