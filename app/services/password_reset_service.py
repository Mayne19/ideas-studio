from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.core import PasswordResetToken, User

logger = logging.getLogger(__name__)

RESET_TOKEN_TTL_MINUTES = 45


def _hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _frontend_base_url() -> str:
    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL.rstrip("/")
    if settings.APP_ENV == "development":
        return "http://localhost:5173"
    return settings.APP_URL.rstrip("/")


def create_password_reset(db: Session, email: str) -> tuple[bool, str | None]:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not user.is_active:
        return False, None

    now = datetime.now(timezone.utc)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )

    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_sha256=_hash_token(raw_token),
        expires_at=now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        created_at=now,
    )
    db.add(reset)
    db.commit()

    reset_url = f"{_frontend_base_url()}/reset-password?token={raw_token}"
    if settings.APP_ENV != "production":
        logger.warning("Development password reset link for %s: %s", email, reset_url)
        return False, reset_url

    logger.info("Password reset requested for user_id=%s but no email provider is configured.", user.id)
    return False, None


def reset_password(db: Session, token: str, password: str) -> bool:
    now = datetime.now(timezone.utc)
    reset = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_sha256 == _hash_token(token),
            PasswordResetToken.used_at.is_(None),
        )
    ).scalar_one_or_none()
    if not reset:
        return False
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        reset.used_at = now
        db.commit()
        return False

    user = db.execute(
        select(User).where(User.id == reset.user_id, User.is_active.is_(True))
    ).scalar_one_or_none()
    if not user:
        reset.used_at = now
        db.commit()
        return False

    user.password_hash = hash_password(password)
    reset.used_at = now
    db.commit()
    return True
