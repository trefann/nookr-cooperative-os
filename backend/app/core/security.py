"""Password hashing and JWT issuing/verification.

bcrypt is used directly rather than through passlib: passlib 1.7.4 reads
bcrypt.__about__.__version__, which bcrypt 4.1+ removed, and crashes at import.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

#: bcrypt silently truncates beyond 72 bytes; reject instead of truncating.
MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes long.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int,
    role: str,
    extra: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    expire_delta = timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def token_expires_in_seconds() -> int:
    return settings.access_token_expire_minutes * 60
