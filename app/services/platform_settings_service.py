"""Réglages globaux de l'instance (core.platform_settings), éditables par le
staff depuis l'interface (Compte → Administration de l'instance)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.core import PlatformSetting

REGISTRATION_KEY = "registration"


def is_open_registration(db: Session) -> bool:
    """Inscription libre sans invitation. Fermée par défaut (absence de ligne)."""
    row = db.get(PlatformSetting, REGISTRATION_KEY)
    return bool(row and (row.value or {}).get("open") is True)


def set_open_registration(db: Session, open_: bool, user_id: str | None) -> bool:
    row = db.get(PlatformSetting, REGISTRATION_KEY)
    if row is None:
        row = PlatformSetting(key=REGISTRATION_KEY, value={})
        db.add(row)
    row.value = {**(row.value or {}), "open": bool(open_)}
    row.updated_by = user_id
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return bool(open_)
