from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    is_active: bool
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime
