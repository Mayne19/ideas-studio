from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember

_bearer = HTTPBearer()


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_project_or_404(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def user_can_access_project(user_id: str, project_id: str, db: Session) -> bool:
    return (
        db.query(ProjectMember)
        .filter(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status == "active",
        )
        .first()
        is not None
    )


def get_project_member(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMember:
    if current_user.is_platform_admin:
        return ProjectMember(
            id=f"platform-admin:{current_user.id}:{project_id}",
            project_id=project_id,
            user_id=current_user.id,
            role="owner",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
    member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.user_id == current_user.id,
            ProjectMember.project_id == project_id,
            ProjectMember.status == "active",
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied: not a project member")
    return member


def require_project_member(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ProjectMember:
    return get_project_member(project_id, current_user, db)


def get_member_for_project(db: Session, user_id: str, project_id: str) -> ProjectMember | None:
    return (
        db.query(ProjectMember)
        .filter(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status == "active",
        )
        .first()
    )


def require_project_role(*allowed_roles: str):
    def dependency(member: ProjectMember = Depends(get_project_member)) -> ProjectMember:
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {allowed_roles}",
            )
        return member

    return dependency
