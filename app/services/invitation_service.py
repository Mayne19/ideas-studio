from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.invitation import Invitation
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.member import MemberPublic


def create_invitation(
    db: Session,
    project_id: str,
    email: str,
    role: str,
    invited_by_user_id: str,
) -> Invitation:
    existing_user = db.query(User).filter(User.email == email).first()
    inv = Invitation(
        project_id=project_id,
        email=email,
        role=role,
        invited_by_user_id=invited_by_user_id,
        target_user_id=existing_user.id if existing_user else None,
    )
    db.add(inv)
    db.flush()
    return inv


def get_invitation_by_token(db: Session, token: str) -> Invitation | None:
    return db.query(Invitation).filter(Invitation.token == token).first()


def accept_invitation(
    db: Session,
    invitation: Invitation,
    user: User,
) -> ProjectMember:
    if invitation.accepted_at:
        raise ValueError("Cette invitation a déjà été acceptée.")
    if datetime.now(timezone.utc) > invitation.expires_at:
        raise ValueError("Cette invitation a expiré.")

    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == invitation.project_id,
            ProjectMember.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise ValueError("Vous êtes déjà membre de ce projet.")

    member = ProjectMember(
        project_id=invitation.project_id,
        user_id=user.id,
        role=invitation.role,
        status="active",
    )
    db.add(member)

    invitation.accepted_at = datetime.now(timezone.utc)
    if not invitation.target_user_id:
        invitation.target_user_id = user.id

    db.flush()
    return _to_public(member, user)


def _to_public(member: ProjectMember, user: User | None) -> MemberPublic:
    return MemberPublic(
        id=member.id,
        user_id=member.user_id,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        role=member.role,
        status=member.status,
        created_at=member.created_at,
    )
