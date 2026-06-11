from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate
from app.core.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    clean = username.strip().lstrip("@").lower()
    return db.query(User).filter(User.username == clean).first()


def create_user(db: Session, data: RegisterRequest) -> User:
    is_first_user = db.query(User.id).first() is None
    kwargs = {
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "is_platform_admin": is_first_user,
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
        user.name = data.name
    if data.username is not None:
        clean = data.username.strip().lstrip("@").lower()
        # Check uniqueness
        existing = db.query(User).filter(User.username == clean, User.id != user.id).first()
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
