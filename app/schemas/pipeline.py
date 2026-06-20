from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PipelineSettings(BaseModel):
    enabled: bool = False
    active_days: list[str] = []
    launch_hour: int = 8
    articles_per_week: int = 5
    category_priorities: dict[str, int] = {}
    ideas_per_week: Optional[int] = 5
    max_pending_drafts: Optional[int] = 10
    paused_until: Optional[datetime] = None
    paused_indefinitely: bool = False
    default_quality_mode: str = "quality"
    launch_hours: Optional[list[str]] = None
    cost_limit_per_article_eur: Optional[float] = None


class PipelineSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    active_days: Optional[list[str]] = None
    launch_hour: Optional[int] = None
    articles_per_week: Optional[int] = None
    category_priorities: Optional[dict[str, int]] = None
    ideas_per_week: Optional[int] = None
    max_pending_drafts: Optional[int] = None
    paused_until: Optional[datetime] = None
    paused_indefinitely: Optional[bool] = None
    default_quality_mode: Optional[str] = None
    launch_hours: Optional[list[str]] = None
    cost_limit_per_article_eur: Optional[float] = None


class CategoryFrequencyInfo(BaseModel):
    id: str
    name: str
    monthly_frequency: Optional[int] = None
    pipeline_enabled: Optional[bool] = None
    priority: int = 0


class PipelineSettingsPublic(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    enabled: bool
    active_days: list[str]
    launch_hour: int
    articles_per_week: int
    category_priorities: dict[str, int]
    ideas_per_week: Optional[int] = None
    max_pending_drafts: Optional[int] = None
    paused_until: Optional[datetime] = None
    paused_indefinitely: Optional[bool] = None
    default_quality_mode: Optional[str] = None
    launch_hours: Optional[list[str]] = None
    cost_limit_per_article_eur: Optional[float] = None
    total_monthly_from_categories: Optional[int] = None
    categories_frequencies: list[CategoryFrequencyInfo] = []
    automation_notes: str = ""
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
