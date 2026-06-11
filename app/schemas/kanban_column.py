from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class KanbanColumnCreate(BaseModel):
    label: str
    status: Optional[str] = None
    color: str = "#007aff"
    sort_order: int = 0


class KanbanColumnUpdate(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class KanbanColumnPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    label: str
    status: str
    color: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
