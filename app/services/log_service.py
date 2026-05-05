import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.article_log import ArticleLog


def log_step(
    db: Session,
    project_id: str,
    message: str,
    level: str = "info",
    step: str | None = None,
    article_id: str | None = None,
) -> ArticleLog:
    entry = ArticleLog(
        id=str(uuid.uuid4()),
        project_id=project_id,
        article_id=article_id,
        level=level,
        step=step,
        message=message,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry
