import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog


def log_activity(
    db: Session,
    project_id: str,
    user_id: str | None,
    user_name: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    description: str | None = None,
    metadata_json: str | None = None,
) -> ActivityLog:
    log = ActivityLog(
        project_id=project_id,
        user_id=user_id,
        user_name=user_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        metadata_json=metadata_json,
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
) -> list[ActivityLog]:
    query = db.query(ActivityLog).filter(ActivityLog.project_id == project_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    return query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
