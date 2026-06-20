from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.dependencies.auth import get_current_user, get_project_member, require_project_role
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectPublic, ProjectConnectInfo
from app.services.publication_revalidation_service import trigger_project_revalidation
from app.services.project_service import (
    create_project,
    delete_project,
    get_user_projects,
    get_project_by_id,
    update_project,
    disconnect_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectPublic])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_projects(db, current_user.id)


@router.post("", response_model=ProjectPublic, status_code=201)
def create_project_route(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_project(db, data, current_user.id)


@router.get("/{project_id}", response_model=ProjectPublic)
def get_project(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return db.query(Project).filter(Project.id == project_id).first()


@router.patch("/{project_id}", response_model=ProjectPublic)
def patch_project(
    project_id: str,
    data: ProjectUpdate,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    return update_project(db, project, data)


@router.get("/{project_id}/connect", response_model=ProjectConnectInfo)
def connect_info(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()

    masked = project.secret_api_key[:8] + "..." + project.secret_api_key[-4:]
    snippet = (
        f'<script\n'
        f'  src="{settings.APP_URL}/traffic.js"\n'
        f'  data-project-id="{project.id}"\n'
        f'  data-tracking-key="{project.public_tracking_key}"\n'
        f'  async>\n'
        f'</script>'
    )

    return ProjectConnectInfo(
        project_id=project.id,
        domain=project.domain,
        status=project.status,
        public_tracking_key=project.public_tracking_key,
        secret_api_key_masked=masked,
        connected_at=project.connected_at,
        last_seen_at=project.last_seen_at,
        snippet=snippet,
        public_api_endpoints={
            "articles": f"{settings.APP_URL}/api/public/projects/{project.id}/articles",
            "article_by_slug": f"{settings.APP_URL}/api/public/projects/{project.id}/articles/{{slug}}",
        },
        public_site_url=project.public_site_url,
        revalidate_url=project.revalidate_url,
        revalidate_secret_configured=bool(project.revalidate_secret_encrypted),
        last_revalidated_at=project.last_revalidated_at,
        last_revalidate_status=project.last_revalidate_status,
        last_revalidate_error=project.last_revalidate_error,
    )


@router.post("/{project_id}/revalidate")
def revalidate_project(
    project_id: str,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return trigger_project_revalidation(db, project, event_type="manual")


@router.delete("/{project_id}", status_code=204)
def delete_project_route(
    project_id: str,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_project(db, project)
    return None


@router.post("/{project_id}/disconnect", response_model=ProjectPublic)
def disconnect_route(
    project_id: str,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    return disconnect_project(db, project)
