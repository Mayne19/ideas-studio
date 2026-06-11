import base64
import hashlib
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
SECRET_PREFIX = "fernet:"


def _secret_fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith(SECRET_PREFIX):
        return value
    encrypted = _secret_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{SECRET_PREFIX}{encrypted}"


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    if not value.startswith(SECRET_PREFIX):
        # Backward-compatible read for existing local configs created before encryption.
        return value
    token = value[len(SECRET_PREFIX):]
    try:
        return _secret_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
