from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    priority: int = 0
    target_frequency: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    target_frequency: Optional[int] = None


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    slug: str
    description: Optional[str]
    priority: int
    target_frequency: Optional[int]
    created_at: datetime
    updated_at: datetime
