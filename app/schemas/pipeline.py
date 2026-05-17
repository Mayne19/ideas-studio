from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PipelineSettings(BaseModel):
    enabled: bool = False
    active_days: list[str] = []
    launch_hour: int = 8
    articles_per_week: int = 5
    category_priorities: dict[str, int] = {}


class PipelineSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    active_days: Optional[list[str]] = None
    launch_hour: Optional[int] = None
    articles_per_week: Optional[int] = None
    category_priorities: Optional[dict[str, int]] = None


class PipelineSettingsPublic(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    enabled: bool
    active_days: list[str]
    launch_hour: int
    articles_per_week: int
    category_priorities: dict[str, int]
    created_at: datetime
    updated_at: datetime


class PipelineLogPublic(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    status: str
    ideas_generated: int
    articles_created: int
    errors: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
