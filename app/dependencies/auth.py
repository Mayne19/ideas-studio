from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db, set_current_project_id
from app.core.security import decode_access_token
from app.models.core import Project, ProjectMember, User
from app.models.reference import MemberRole, MembershipStatus

_bearer = HTTPBearer()

# Rôles textuels (role.name) utilisés côté routers/permissions — l'ordre
# reflète le rank croissant de ref.member_roles.
ROLE_CODE_BY_RANK = {
    MemberRole.VIEWER: "viewer",
    MemberRole.DESIGNER: "designer",
    MemberRole.EDITOR: "editor",
    MemberRole.ADMIN: "admin",
    MemberRole.OWNER: "owner",
}
ROLE_RANK_BY_CODE = {v: k for k, v in ROLE_CODE_BY_RANK.items()}
# Alias rétrocompatibles (préfixe _ historique) — voir app/routers/members.py
_ROLE_CODE_BY_RANK = ROLE_CODE_BY_RANK
_ROLE_RANK_BY_CODE = ROLE_RANK_BY_CODE


class MemberView:
    """Vue de compatibilité exposant `.role` (str) par-dessus
    ProjectMember.role_id (int) — évite de réécrire chaque comparaison de
    rôle du routeur en une passe ; les routers migrent vers role_id
    directement au fur et à mesure (voir REPRENDRE-LA-MAIN.md §6 étape 7)."""

    def __init__(self, member: ProjectMember, role_code: str):
        self._member = member
        self.role = role_code

    def __getattr__(self, name):
        return getattr(self._member, name)


def _role_code(role_id: int) -> str:
    return ROLE_CODE_BY_RANK.get(role_id, "viewer")


role_code = _role_code


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_project_or_404(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def user_can_access_project(user_id: str, project_id: str, db: Session) -> bool:
    return db.execute(
        select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none() is not None


def get_project_member(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberView:
    """Un utilisateur n'a accès qu'aux projets dont il est explicitement
    membre — is_staff ne donne plus jamais d'accès virtuel cross-projet
    (ancien comportement retiré : il fabriquait un ProjectMember owner
    fictif sur N'IMPORTE QUEL project_id, contraire au modèle voulu où
    le créateur d'un projet est owner de CE projet et rien d'autre).
    is_staff reste utilisé ailleurs uniquement pour le catalogue de
    providers IA partagé au niveau plateforme (ai_providers.py,
    ai_agents.py), qui ne touche aucune donnée de projet."""
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.user_id == current_user.id,
            ProjectMember.project_id == project_id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied: not a project member")
    set_current_project_id(project_id)
    return MemberView(member, _role_code(member.role_id))


def require_project_member(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberView:
    return get_project_member(project_id, current_user, db)


def get_member_for_project(db: Session, user_id: str, project_id: str) -> MemberView | None:
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if not member:
        return None
    set_current_project_id(project_id)
    return MemberView(member, _role_code(member.role_id))


def require_project_role(*allowed_roles: str):
    def dependency(member: MemberView = Depends(get_project_member)) -> MemberView:
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {allowed_roles}",
            )
        return member

    return dependency
