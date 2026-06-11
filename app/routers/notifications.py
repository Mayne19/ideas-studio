from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member
from app.models.notification import Notification
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.notification import NotificationPublic

router = APIRouter(tags=["notifications"])


@router.get("/projects/{project_id}/notifications", response_model=list[NotificationPublic])
def list_notifications(
    project_id: str,
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
):
    return (
        db.query(Notification)
        .filter(Notification.project_id == project_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
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

    return notif


@router.post("/projects/{project_id}/notifications/read-all", response_model=dict)
def mark_all_notifications_read(
    project_id: str,
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
):
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(
            Notification.project_id == project_id,
            Notification.read_at.is_(None),
        )
        .all()
    )
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
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, current_user.id, notif.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")

    db.delete(notif)
    db.commit()
    return None
