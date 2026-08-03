from typing import Optional
from pydantic import BaseModel


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
    id: str
    project_id: str
    label: str
    status: str
    color: Optional[str] = None
    sort_order: int
