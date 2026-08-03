import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ops import EventLog
from app.models.reference import LogLevel


def log_activity(
    db: Session,
    project_id: str,
    user_id: str | None,
    user_name: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    description: str | None = None,
    metadata: dict | None = None,
) -> EventLog:
    context = dict(metadata or {})
    if user_name:
        context["user_name"] = user_name
    if resource_type:
        context["resource_type"] = resource_type
    if resource_id:
        context["resource_id"] = resource_id

    log = EventLog(
        id=str(uuid.uuid4()),
        occurred_at=datetime.now(timezone.utc),
        project_id=project_id,
        actor_id=user_id,
        level_id=LogLevel.INFO,
        scope="activity",
        action=action,
        message=description,
        context=context,
    )
    db.add(log)
    db.commit()
    return log


def get_project_activity(
    db: Session,
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
) -> list[EventLog]:
    query = select(EventLog).where(EventLog.project_id == project_id, EventLog.scope == "activity")
    if action:
        query = query.where(EventLog.action == action)
    query = query.order_by(EventLog.occurred_at.desc()).offset(offset).limit(limit)
    return db.execute(query).scalars().all()
