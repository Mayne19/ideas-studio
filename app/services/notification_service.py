from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    project_id: str,
    title: str,
    message: str,
    level: str = "info",
    type: str = "system",
    user_id: str | None = None,
) -> Notification:
    notif = Notification(
        project_id=project_id,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        level=level,
    )
    db.add(notif)
    db.flush()
    return notif
