from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, role_code
from app.models.core import Project, User
from app.schemas.invitation import InvitationInfo
from app.services.invitation_service import accept_invitation, get_invitation_by_token
from app.services.notification_service import create_notification

router = APIRouter(prefix="/invitations", tags=["invitations"])


def _user_display_name(user: User) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip()


@router.get("/{token}", response_model=InvitationInfo)
def get_invitation(token: str, db: Session = Depends(get_db)):
    inv = get_invitation_by_token(db, token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation introuvable ou lien invalide.")
    project = db.get(Project, inv.project_id)
    return InvitationInfo(
        project_name=project.name if project else "Projet",
        role=role_code(inv.role_id),
        email=inv.email,
        expires_at=inv.expires_at,
        already_accepted=inv.accepted_at is not None,
        expired=datetime.now(timezone.utc) > inv.expires_at,
    )


@router.post("/{token}/accept", response_model=dict)
def accept_invitation_route(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = get_invitation_by_token(db, token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation introuvable.")

    try:
        accept_invitation(db, inv, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    project = db.get(Project, inv.project_id)
    create_notification(
        db, inv.project_id,
        title="Invitation acceptée",
        message=f"{_user_display_name(current_user)} a rejoint le projet {project.name if project else ''}.",
        level="success",
        type="invitation",
    )
    db.commit()
    return {"message": "Vous avez rejoint le projet avec succès."}
