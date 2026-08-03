"""core.invitations.token_sha256 remplace l'ancien token en clair — même
principe que app/services/password_reset_service.py : le jeton brut n'est
récupérable qu'à la création, seul son digest est stocké ensuite."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Invitation, ProjectMember, User
from app.models.reference import MembershipStatus

INVITATION_TTL_DAYS = 14


def _hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def create_invitation(
    db: Session,
    project_id: str,
    email: str,
    role_id: int,
    invited_by_user_id: str,
) -> tuple[Invitation, str]:
    existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    raw_token = secrets.token_urlsafe(32)
    inv = Invitation(
        project_id=project_id,
        email=email,
        role_id=role_id,
        token_sha256=_hash_token(raw_token),
        invited_by=invited_by_user_id,
        accepted_by=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_TTL_DAYS),
    )
    db.add(inv)
    db.flush()
    return inv, raw_token


def get_invitation_by_token(db: Session, token: str) -> Invitation | None:
    return db.execute(
        select(Invitation).where(Invitation.token_sha256 == _hash_token(token))
    ).scalar_one_or_none()


def accept_invitation(db: Session, invitation: Invitation, user: User) -> ProjectMember:
    if invitation.accepted_at:
        raise ValueError("Cette invitation a déjà été acceptée.")
    if datetime.now(timezone.utc) > invitation.expires_at:
        raise ValueError("Cette invitation a expiré.")
    if user.email != invitation.email:
        raise ValueError("Cette invitation ne vous est pas destinée.")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == invitation.project_id,
            ProjectMember.user_id == user.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Vous êtes déjà membre de ce projet.")

    member = ProjectMember(
        project_id=invitation.project_id,
        user_id=user.id,
        role_id=invitation.role_id,
    )
    member.status_reason_id = MembershipStatus.ACTIVE
    member.state_id = 0
    db.add(member)

    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_by = user.id

    db.flush()
    return member
