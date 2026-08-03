import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.ops import EventLog
from app.models.reference import LogLevel

_LEVEL_BY_NAME = {
    "debug": LogLevel.DEBUG,
    "info": LogLevel.INFO,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
}


def log_step(
    db: Session,
    project_id: str,
    message: str,
    level: str = "info",
    step: str | None = None,
    article_id: str | None = None,
) -> EventLog:
    entry = EventLog(
        id=str(uuid.uuid4()),
        occurred_at=datetime.now(timezone.utc),
        project_id=project_id,
        article_id=article_id,
        level_id=_LEVEL_BY_NAME.get(level, LogLevel.INFO),
        scope="generation",
        action=step or "orchestrator",
        message=message,
    )
    db.add(entry)
    db.flush()
    return entry
