from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

ASSIGNABLE_ROLES = frozenset({"admin", "editor", "writer", "viewer"})


class MemberAdd(BaseModel):
    user_id: str
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ASSIGNABLE_ROLES:
            raise ValueError(f"role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}")
        return v


class MemberPatch(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ASSIGNABLE_ROLES:
            raise ValueError(f"role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}")
        return v


class MemberPublic(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: str
    status: str
    created_at: datetime
