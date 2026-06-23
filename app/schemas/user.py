import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lstrip("@")
        if not USERNAME_RE.match(v):
            raise ValueError("Le nom d'utilisateur ne peut contenir que des lettres, chiffres et tirets bas.")
        if len(v) < 2:
            raise ValueError("Le nom d'utilisateur doit contenir au moins 2 caractères.")
        return v.lower()


class UsernameCheck(BaseModel):
    username: str


class UsernameAvailable(BaseModel):
    available: bool


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: Optional[str] = None
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    avatar_url: Optional[str] = None
    is_active: bool
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime
