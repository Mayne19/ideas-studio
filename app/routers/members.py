from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.member import MemberAdd, MemberPatch, MemberPublic
from app.schemas.invitation import InvitationCreate, InvitationPublic
from app.services.auth_service import get_user_by_username
from app.services.notification_service import create_notification

router = APIRouter(prefix="/projects", tags=["members"])


def _to_public(member: ProjectMember, user: User | None) -> MemberPublic:
    return MemberPublic(
        id=member.id,
        user_id=member.user_id,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        user_username=user.username if user else None,
        role=member.role,
        status=member.status,
        created_at=member.created_at,
    )


@router.get("/{project_id}/members", response_model=list[MemberPublic])
def list_members(
    project_id: str,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at)
        .all()
    )
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        result.append(_to_public(m, user))
    return result


@router.post("/{project_id}/members", response_model=MemberPublic, status_code=201)
def add_member_by_id(
    project_id: str,
    data: MemberAdd,
    actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this project")

    new_member = ProjectMember(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role,
        status="active",
    )
    db.add(new_member)
    create_notification(
        db, project_id,
        title="Nouveau membre",
        message=f"{target_user.name} a été ajouté au projet.",
        level="success",
        type="member",
        user_id=data.user_id,
    )
    db.commit()
    db.refresh(new_member)
    return _to_public(new_member, target_user)


@router.post("/{project_id}/members/by-username", response_model=MemberPublic, status_code=201)
def add_member_by_username(
    project_id: str,
    data: MemberAdd,
    actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    clean = data.user_id.strip().lstrip("@").lower()
    target_user = get_user_by_username(db, clean)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="L'utilisateur est déjà membre de ce projet.")

    new_member = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        role=data.role,
        status="active",
    )
    db.add(new_member)
    create_notification(
        db, project_id,
        title="Nouveau membre",
        message=f"{target_user.name} (@{target_user.username}) a été ajouté au projet.",
        level="success",
        type="member",
    )
    db.commit()
    db.refresh(new_member)
    return _to_public(new_member, target_user)


@router.get("/{project_id}/invitations", response_model=list[InvitationPublic])
def list_invitations(
    project_id: str,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    invitations = (
        db.query(Invitation)
        .filter(Invitation.project_id == project_id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    return invitations


@router.post("/{project_id}/invitations", response_model=InvitationPublic, status_code=201)
def invite_by_email(
    project_id: str,
    data: InvitationCreate,
    actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        already_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == existing_user.id,
            )
            .first()
        )
        if already_member:
            raise HTTPException(status_code=409, detail="Cet utilisateur est déjà membre du projet.")

    inv = Invitation(
        project_id=project_id,
        email=data.email,
        role=data.role,
        invited_by_user_id=actor.user_id,
        target_user_id=existing_user.id if existing_user else None,
    )
    db.add(inv)
    create_notification(
        db, project_id,
        title="Invitation créée",
        message=f"Une invitation a été créée pour {data.email} avec le rôle {data.role}. Copiez le lien si l'envoi email n'est pas configuré.",
        level="info",
        type="invitation",
    )
    db.commit()
    db.refresh(inv)
    return inv


@router.patch("/{project_id}/members/{target_user_id}", response_model=MemberPublic)
def patch_member(
    project_id: str,
    target_user_id: str,
    data: MemberPatch,
    actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if target_user_id == project.owner_id:
        raise HTTPException(status_code=403, detail="Cannot change the role of the project owner")

    target = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    old_role = target.role
    target.role = data.role
    create_notification(
        db, project_id,
        title="Rôle modifié",
        message=f"Le rôle de {target_user_id} est passé de {old_role} à {data.role}.",
        level="info",
        type="member",
    )
    db.commit()
    db.refresh(target)
    user = db.query(User).filter(User.id == target.user_id).first()
    return _to_public(target, user)


@router.delete("/{project_id}/members/{target_user_id}")
def remove_member(
    project_id: str,
    target_user_id: str,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if target_user_id == project.owner_id:
        raise HTTPException(status_code=403, detail="Cannot remove the project owner")

    target = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(target)
    db.commit()
    return {"message": "Member removed from project"}


