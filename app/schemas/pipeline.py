from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PipelineSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    active_days: Optional[list[str]] = None
    launch_hour: Optional[int] = None
    ideas_day_of_month: Optional[int] = None
    publish_hour_start: Optional[int] = None
    publish_hour_end: Optional[int] = None
    articles_per_week: Optional[int] = None
    category_priorities: Optional[dict[str, int]] = None
    ideas_per_week: Optional[int] = None
    max_pending_drafts: Optional[int] = None
    max_parallel_writing_jobs: Optional[int] = None
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
    priority: float = 0


class PipelineSettingsPublic(BaseModel):
    project_id: str
    enabled: bool
    active_days: list[str] = []
    launch_hour: int = 8
    articles_per_week: int
    category_priorities: dict[str, int] = {}
    ideas_per_week: Optional[int] = None
    max_pending_drafts: Optional[int] = None
    max_parallel_writing_jobs: Optional[int] = None
    paused_until: Optional[datetime] = None
    paused_indefinitely: Optional[bool] = None
    default_quality_mode: Optional[str] = None
    ideas_day_of_month: Optional[int] = None
    publish_hour_start: Optional[int] = 8
    publish_hour_end: Optional[int] = 10
    launch_hours: Optional[list[str]] = None
    cost_limit_per_article_eur: Optional[float] = None
    total_monthly_from_categories: Optional[int] = None
    categories_frequencies: list[CategoryFrequencyInfo] = []
    automation_notes: str = ""
    updated_at: datetime


class PipelineLogPublic(BaseModel):
    id: str
    project_id: str
    status: str
    workflow_run_id: str | None = None
    expected_ideas: int = 0
    generated_ideas: int = 0
    failed_categories: list[dict] = []
    run_errors: list[str] = []
    ideas_generated: int
    articles_created: int
    errors: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
