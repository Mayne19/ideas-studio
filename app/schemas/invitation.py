from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from app.schemas.member import ASSIGNABLE_ROLES


class InvitationCreate(BaseModel):
    email: str
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ASSIGNABLE_ROLES:
            raise ValueError(f"role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}")
        return v


class InvitationPublic(BaseModel):
    id: str
    project_id: str
    email: str
    role: str
    token: str
    invited_by_user_id: str
    target_user_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime


class InvitationInfo(BaseModel):
    project_name: str
    role: str
    email: str
    token: str
    expires_at: datetime
    already_accepted: bool = False
    expired: bool = False
