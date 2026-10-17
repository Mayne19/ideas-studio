"""Daily capacity rules for the local writer queue."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import Pipeline
from app.models.content import Article
from app.models.reference import ArticleStatus

DEFAULT_WRITING_DAYS = [0, 1, 2, 3, 4]
_COUNTED_TODAY = (
    ArticleStatus.WRITING_REQUESTED,
    ArticleStatus.WRITING_IN_PROGRESS,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.REVIEW_NEEDED,
)


def queue_capacity(db: Session, project_id: str, *, now: datetime | None = None) -> int:
    """Return how many local-writer subjects may be handed out now."""
    current = now or datetime.now(timezone.utc)
    pipeline = db.get(Pipeline, project_id)
    schedule = (pipeline.schedule if pipeline else {}) or {}
    writing_days = schedule.get("writing_days", DEFAULT_WRITING_DAYS)
    if current.weekday() not in writing_days:
        return 0

    limit = max(0, int(pipeline.articles_per_day if pipeline else 2))
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    started_today = db.execute(
        select(func.count())
        .select_from(Article)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id.in_(_COUNTED_TODAY),
            Article.updated_at >= start,
        )
    ).scalar_one()
    return max(0, limit - int(started_today))
