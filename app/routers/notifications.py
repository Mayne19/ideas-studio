from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_project_member
from app.models.ops import Notification
from app.models.core import User
from app.models.reference import LogLevel
from app.schemas.notification import NotificationPublic

router = APIRouter(tags=["notifications"])

_LEVEL_CODE_BY_ID = {
    LogLevel.DEBUG: "debug",
    LogLevel.INFO: "info",
    LogLevel.WARNING: "warning",
    LogLevel.ERROR: "error",
}


def _to_public(notif: Notification) -> NotificationPublic:
    return NotificationPublic(
        id=notif.id,
        project_id=notif.project_id,
        user_id=notif.user_id,
        type=notif.type,
        title=notif.title,
        message=notif.body,
        level=_LEVEL_CODE_BY_ID.get(notif.level_id, "info"),
        link=notif.link,
        read_at=notif.read_at,
        created_at=notif.created_at,
    )


@router.get("/projects/{project_id}/notifications", response_model=list[NotificationPublic])
def list_notifications(
    project_id: str,
    db: Session = Depends(get_db),
    member: MemberView = Depends(get_project_member),
):
    notifs = db.execute(
        select(Notification)
        .where(Notification.project_id == project_id)
        .order_by(Notification.created_at.desc())
    ).scalars().all()
    return [_to_public(n) for n in notifs]


@router.post("/notifications/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, current_user.id, notif.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")

    if not notif.read_at:
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)

    return _to_public(notif)


@router.post("/projects/{project_id}/notifications/read-all", response_model=dict)
def mark_all_notifications_read(
    project_id: str,
    db: Session = Depends(get_db),
    member: MemberView = Depends(get_project_member),
):
    now = datetime.now(timezone.utc)
    updated = db.execute(
        select(Notification).where(
            Notification.project_id == project_id,
            Notification.read_at.is_(None),
        )
    ).scalars().all()
    for n in updated:
        n.read_at = now
    db.commit()
    return {"marked_read": len(updated)}


@router.delete("/notifications/{notification_id}", status_code=204)
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, current_user.id, notif.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")

    db.delete(notif)
    db.commit()
    return None
