from sqlalchemy.orm import Session

from app.models.ops import Notification
from app.models.reference import LogLevel

_LEVEL_BY_NAME = {
    "debug": LogLevel.DEBUG,
    "info": LogLevel.INFO,
    "success": LogLevel.INFO,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
}


def create_notification(
    db: Session,
    project_id: str,
    title: str,
    message: str,
    level: str = "info",
    type: str = "system",
    user_id: str | None = None,
    link: str | None = None,
) -> Notification:
    notif = Notification(
        project_id=project_id,
        user_id=user_id,
        type=type,
        title=title,
        body=message,
        level_id=_LEVEL_BY_NAME.get(level, LogLevel.INFO),
        link=link,
    )
    db.add(notif)
    db.flush()
    return notif
