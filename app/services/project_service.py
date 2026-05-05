import secrets
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.project import ProjectCreate, ProjectUpdate


def _generate_key() -> str:
    return secrets.token_urlsafe(48)


def create_project(db: Session, data: ProjectCreate, owner_id: str) -> Project:
    project = Project(
        owner_id=owner_id,
        name=data.name,
        domain=data.domain,
        language=data.language,
        country_target=data.country_target,
        audience=data.audience,
        tone=data.tone,
        public_tracking_key=_generate_key(),
        secret_api_key=_generate_key(),
        status="not_connected",
    )
    db.add(project)
    db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=owner_id,
        role="owner",
        status="active",
    )
    db.add(member)
    db.commit()
    db.refresh(project)
    return project


def get_user_projects(db: Session, user_id: str) -> list[Project]:
    return (
        db.query(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(ProjectMember.user_id == user_id, ProjectMember.status == "active")
        .all()
    )


def get_project_by_id(db: Session, project_id: str) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project
