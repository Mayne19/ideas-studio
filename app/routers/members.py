from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_project_member, require_project_role
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.member import MemberAdd, MemberPatch, MemberPublic

router = APIRouter(prefix="/projects", tags=["members"])


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


@router.get("/{project_id}/members", response_model=list[MemberPublic])
def list_members(
    project_id: str,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        result.append(_to_public(m, user))
    return result


@router.post("/{project_id}/members", response_model=MemberPublic, status_code=201)
def add_member(
    project_id: str,
    data: MemberAdd,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin")),
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
    db.commit()
    db.refresh(new_member)
    return _to_public(new_member, target_user)


@router.patch("/{project_id}/members/{target_user_id}", response_model=MemberPublic)
def patch_member(
    project_id: str,
    target_user_id: str,
    data: MemberPatch,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin")),
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

    target.role = data.role
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
