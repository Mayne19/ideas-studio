from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Bornes des réglages projet éditables depuis Paramètres → Pipeline.
IDEAS_PER_RUN_MIN = 1
IDEAS_PER_RUN_MAX = 3
DEFAULT_IDEAS_PER_RUN = 2
MIN_PUBLISH_SCORE_MIN = 85
MIN_PUBLISH_SCORE_MAX = 100
DEFAULT_MIN_PUBLISH_SCORE = 90


class PipelineSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    active_days: Optional[list[str]] = None
    launch_hour: Optional[int] = None
    # Fréquence de génération des idées : daily, weekly, monthly, quarterly.
    # launch_day s'interprète selon la fréquence : ignoré si daily, jour de la
    # semaine 0=lundi..6=dimanche si weekly, jour du mois (1-31) si monthly ou
    # quarterly (auquel cas le mois doit aussi être un multiple du cycle de 3
    # depuis l'activation — voir app.services.scheduler_service).
    ideas_frequency: Optional[str] = None
    launch_day: Optional[int] = None
    ideas_day_of_month: Optional[int] = None
    publish_hour_start: Optional[int] = None
    publish_hour_end: Optional[int] = None
    articles_per_week: Optional[int] = None
    category_priorities: Optional[dict[str, int]] = None
    ideas_per_week: Optional[int] = None
    # Plafond dur d'idées créées par lancement (économie de crédits LLM).
    ideas_per_run: Optional[int] = Field(default=None, ge=IDEAS_PER_RUN_MIN, le=IDEAS_PER_RUN_MAX)
    # Score global minimum pour autoriser la publication.
    min_publish_score: Optional[int] = Field(default=None, ge=MIN_PUBLISH_SCORE_MIN, le=MIN_PUBLISH_SCORE_MAX)
    # « agent » : agent rédacteur unique ; « pipeline » : ancienne chaîne.
    generation_mode: Optional[Literal["agent", "pipeline"]] = None
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
    ideas_frequency: str = "monthly"
    launch_day: Optional[int] = None
    articles_per_week: int
    category_priorities: dict[str, int] = {}
    ideas_per_week: Optional[int] = None
    ideas_per_run: int = DEFAULT_IDEAS_PER_RUN
    min_publish_score: int = DEFAULT_MIN_PUBLISH_SCORE
    generation_mode: str = "agent"
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
