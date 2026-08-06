from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models.core import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate
from app.core.security import hash_password, verify_password

# Clé arbitraire distincte de _MIGRATION_ADVISORY_LOCK_KEY (app/main.py) —
# même mécanisme pg_advisory_lock, pour un usage différent (voir
# _is_first_user_atomic ci-dessous).
_FIRST_USER_ADVISORY_LOCK_KEY = 727272


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_username(db: Session, username: str) -> User | None:
    clean = username.strip().lstrip("@").lower()
    return db.execute(select(User).where(User.username == clean)).scalar_one_or_none()


def _is_first_user_atomic(db: Session) -> bool:
    """Le premier compte inscrit reçoit is_staff=True (bootstrap admin sans
    interface d'invitation dédiée — voir app/routers/ai_agents.py:21).

    Sans verrou, deux POST /auth/register concurrents sur une base vide
    peuvent tous deux voir "aucun utilisateur" (SELECT ... LIMIT 1 sous
    READ COMMITTED, l'isolation par défaut ici) et devenir staff tous les
    deux. pg_advisory_lock sérialise ce check-and-decide au niveau process,
    le verrou est libéré automatiquement à la fin de la transaction
    (session-level lock, cohérent avec le commit() de create_user)."""
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _FIRST_USER_ADVISORY_LOCK_KEY})
    return db.execute(select(User.id).limit(1)).scalar_one_or_none() is None


def create_user(db: Session, data: RegisterRequest) -> User:
    is_first_user = _is_first_user_atomic(db)
    name = data.name or f"{data.first_name or ''} {data.last_name or ''}".strip()
    kwargs = {
        "first_name": data.first_name or (name.split(" ")[0] if name else None),
        "last_name": data.last_name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "is_staff": is_first_user,
    }
    if data.username:
        clean = data.username.strip().lstrip("@").lower()
        kwargs["username"] = clean
    user = User(**kwargs)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    if data.name is not None:
        parts = data.name.split(" ", 1)
        user.first_name = parts[0] or None
        user.last_name = parts[1] if len(parts) > 1 else None
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.username is not None:
        clean = data.username.strip().lstrip("@").lower()
        existing = db.execute(
            select(User).where(User.username == clean, User.id != user.id)
        ).scalar_one_or_none()
        if existing:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris.")
        user.username = clean
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
