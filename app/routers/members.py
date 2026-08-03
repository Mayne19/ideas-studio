from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_project_member, require_project_role, _role_code, _ROLE_RANK_BY_CODE
from app.models.core import Invitation, Project, ProjectMember, User
from app.models.reference import MemberRole, MembershipStatus
from app.schemas.member import MemberAdd, MemberPatch, MemberPublic
from app.schemas.invitation import InvitationCreate, InvitationPublic
from app.services.auth_service import get_user_by_username
from app.services.invitation_service import create_invitation
from app.services.notification_service import create_notification

router = APIRouter(prefix="/projects", tags=["members"])

_STATUS_CODE_BY_ID = {
    MembershipStatus.INVITED: "invited",
    MembershipStatus.ACTIVE: "active",
    MembershipStatus.SUSPENDED: "suspended",
    MembershipStatus.REMOVED: "removed",
}


def _user_display_name(user: User) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip()


def _to_public(member: ProjectMember, user: User | None) -> MemberPublic:
    return MemberPublic(
        user_id=member.user_id,
        user_name=_user_display_name(user) if user else None,
        user_email=user.email if user else None,
        user_username=user.username if user else None,
        role=_role_code(member.role_id),
        status=_STATUS_CODE_BY_ID.get(member.status_reason_id, "active"),
        created_at=member.created_at,
    )


def _invitation_to_public(inv: Invitation, raw_token: str | None = None) -> InvitationPublic:
    return InvitationPublic(
        id=inv.id,
        project_id=inv.project_id,
        email=inv.email,
        role=_role_code(inv.role_id),
        token=raw_token,
        invited_by_user_id=inv.invited_by,
        target_user_id=inv.accepted_by,
        accepted_at=inv.accepted_at,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
    )


@router.get("/{project_id}/members/me", response_model=MemberPublic)
def get_my_membership(
    project_id: str,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    user = db.get(User, member.user_id)
    return _to_public(member._member, user)


@router.get("/{project_id}/members", response_model=list[MemberPublic])
def list_members(
    project_id: str,
    _member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    members = db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at)
    ).scalars().all()
    result = []
    for m in members:
        user = db.get(User, m.user_id)
        result.append(_to_public(m, user))
    return result


@router.post("/{project_id}/members", response_model=MemberPublic, status_code=201)
def add_member_by_id(
    project_id: str,
    data: MemberAdd,
    actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    target_user = db.get(User, data.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this project")

    new_member = ProjectMember(
        project_id=project_id,
        user_id=data.user_id,
        role_id=_ROLE_RANK_BY_CODE[data.role],
    )
    new_member.status_reason_id = MembershipStatus.ACTIVE
    new_member.state_id = 0
    db.add(new_member)
    create_notification(
        db, project_id,
        title="Nouveau membre",
        message=f"{_user_display_name(target_user)} a été ajouté au projet.",
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
    actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    clean = data.user_id.strip().lstrip("@").lower()
    target_user = get_user_by_username(db, clean)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="L'utilisateur est déjà membre de ce projet.")

    new_member = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        role_id=_ROLE_RANK_BY_CODE[data.role],
    )
    new_member.status_reason_id = MembershipStatus.ACTIVE
    new_member.state_id = 0
    db.add(new_member)
    create_notification(
        db, project_id,
        title="Nouveau membre",
        message=f"{_user_display_name(target_user)} (@{target_user.username}) a été ajouté au projet.",
        level="success",
        type="member",
    )
    db.commit()
    db.refresh(new_member)
    return _to_public(new_member, target_user)


@router.get("/{project_id}/invitations", response_model=list[InvitationPublic])
def list_invitations(
    project_id: str,
    _actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    invitations = db.execute(
        select(Invitation)
        .where(Invitation.project_id == project_id)
        .order_by(Invitation.created_at.desc())
    ).scalars().all()
    return [_invitation_to_public(inv) for inv in invitations]


@router.post("/{project_id}/invitations", response_model=InvitationPublic, status_code=201)
def invite_by_email(
    project_id: str,
    data: InvitationCreate,
    actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    existing_user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if existing_user:
        already_member = db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == existing_user.id,
            )
        ).scalar_one_or_none()
        if already_member:
            raise HTTPException(status_code=409, detail="Cet utilisateur est déjà membre du projet.")

    inv, raw_token = create_invitation(db, project_id, data.email, _ROLE_RANK_BY_CODE[data.role], actor.user_id)
    create_notification(
        db, project_id,
        title="Invitation créée",
        message=f"Une invitation a été créée pour {data.email} avec le rôle {data.role}. Copiez le lien si l'envoi email n'est pas configuré.",
        level="info",
        type="invitation",
    )
    db.commit()
    db.refresh(inv)
    return _invitation_to_public(inv, raw_token=raw_token)


@router.patch("/{project_id}/members/{target_user_id}", response_model=MemberPublic)
def patch_member(
    project_id: str,
    target_user_id: str,
    data: MemberPatch,
    actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    target = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role_id == MemberRole.OWNER:
        raise HTTPException(status_code=403, detail="Cannot change the role of the project owner")

    old_role = _role_code(target.role_id)
    target.role_id = _ROLE_RANK_BY_CODE[data.role]
    create_notification(
        db, project_id,
        title="Rôle modifié",
        message=f"Le rôle de {target_user_id} est passé de {old_role} à {data.role}.",
        level="info",
        type="member",
    )
    db.commit()
    db.refresh(target)
    user = db.get(User, target.user_id)
    return _to_public(target, user)


@router.delete("/{project_id}/invitations/{invitation_id}")
def remove_invitation(
    project_id: str,
    invitation_id: str,
    _actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    inv = db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation introuvable.")
    db.delete(inv)
    db.commit()
    return {"message": "Invitation supprimée."}


@router.delete("/{project_id}/members/{target_user_id}")
def remove_member(
    project_id: str,
    target_user_id: str,
    _actor: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    target = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role_id == MemberRole.OWNER:
        raise HTTPException(status_code=403, detail="Cannot remove the project owner")

    db.delete(target)
    db.commit()
    return {"message": "Member removed from project"}
