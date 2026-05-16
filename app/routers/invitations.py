from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.invitation import Invitation
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.invitation import InvitationInfo
from app.services.notification_service import create_notification

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("/{token}", response_model=InvitationInfo)
def get_invitation(token: str, db: Session = Depends(get_db)):
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation introuvable ou lien invalide.")
    project = db.query(Project).filter(Project.id == inv.project_id).first()
    return InvitationInfo(
        project_name=project.name if project else "Projet",
        role=inv.role,
        email=inv.email,
        token=inv.token,
        expires_at=inv.expires_at,
        already_accepted=inv.accepted_at is not None,
        expired=datetime.now(timezone.utc) > inv.expires_at,
    )


@router.post("/{token}/accept", response_model=dict)
def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation introuvable.")
    if inv.accepted_at:
        raise HTTPException(status_code=400, detail="Cette invitation a déjà été acceptée.")
    if datetime.now(timezone.utc) > inv.expires_at:
        raise HTTPException(status_code=400, detail="Cette invitation a expiré.")
    if current_user.email != inv.email:
        raise HTTPException(status_code=403, detail="Cette invitation ne vous est pas destinée.")

    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == inv.project_id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Vous êtes déjà membre de ce projet.")

    member = ProjectMember(
        project_id=inv.project_id,
        user_id=current_user.id,
        role=inv.role,
        status="active",
    )
    db.add(member)
    inv.accepted_at = datetime.now(timezone.utc)
    if not inv.target_user_id:
        inv.target_user_id = current_user.id

    project = db.query(Project).filter(Project.id == inv.project_id).first()
    create_notification(
        db, inv.project_id,
        title="Invitation acceptée",
        message=f"{current_user.name} a rejoint le projet {project.name if project else ''}.",
        level="success",
        type="invitation",
    )
    db.commit()
    return {"message": "Vous avez rejoint le projet avec succès."}
