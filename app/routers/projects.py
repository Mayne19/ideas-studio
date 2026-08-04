from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, MemberView
from app.models.core import Project, ProjectCredential, User
from app.models.reference import CredentialKind
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectPublic, ProjectConnectInfo
from app.services.publication_revalidation_service import trigger_project_revalidation
from app.services.project_service import (
    create_project,
    delete_project,
    get_user_projects,
    get_project_by_id,
    serialize_project,
    update_project,
    disconnect_project,
    rotate_revalidate_secret,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    return serialize_project(db, project)


@router.patch("/{project_id}", response_model=ProjectPublic)
def patch_project(
    project_id: str,
    data: ProjectUpdate,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    return update_project(db, project, data)


@router.get("/{project_id}/connect", response_model=ProjectConnectInfo)
def connect_info(
    project_id: str,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    info = serialize_project(db, project)

    tracking_masked = f"{info['public_tracking_key_prefix']}..." if info["public_tracking_key_prefix"] else None
    api_cred = db.execute(
        select(ProjectCredential).where(
            ProjectCredential.project_id == project.id,
            ProjectCredential.kind == CredentialKind.API,
            ProjectCredential.revoked_at.is_(None),
        )
    ).scalars().first()
    api_masked = f"{api_cred.token_prefix}..." if api_cred else None

    snippet = (
        f'<script\n'
        f'  src="{settings.APP_URL}/traffic.js"\n'
        f'  data-project-id="{project.id}"\n'
        f'  data-tracking-key="{tracking_masked or ""}"\n'
        f'  async>\n'
        f'</script>'
    )

    return ProjectConnectInfo(
        project_id=project.id,
        domain=info["domain"],
        status=info["status"],
        public_tracking_key=tracking_masked,
        secret_api_key_masked=api_masked,
        connected_at=info["connected_at"],
        last_seen_at=info["last_seen_at"],
        snippet=snippet,
        public_api_endpoints={
            "articles": f"{settings.APP_URL}/api/public/projects/{project.id}/articles",
            "article_by_slug": f"{settings.APP_URL}/api/public/projects/{project.id}/articles/{{slug}}",
        },
        public_site_url=info["public_site_url"],
        revalidate_url=info["revalidate_url"],
        revalidate_configured=info["revalidate_configured"],
        last_revalidated_at=info["last_revalidated_at"],
        last_revalidate_status=info["last_revalidate_status"],
        last_revalidate_error=info["last_revalidate_error"],
        ga4_property_id=info["ga4_property_id"],
        ga4_configured=info["ga4_configured"],
    )


@router.post("/{project_id}/revalidate")
def revalidate_project(
    project_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    return trigger_project_revalidation(db, project, event_type="manual")


@router.post("/{project_id}/revalidate-secret/rotate")
def rotate_revalidate_secret_route(
    project_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    new_secret = rotate_revalidate_secret(db, project)
    return {"revalidate_secret": new_secret}


@router.delete("/{project_id}", status_code=204)
def delete_project_route(
    project_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    delete_project(db, project)
    return None


@router.post("/{project_id}/disconnect", response_model=ProjectPublic)
def disconnect_route(
    project_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    return disconnect_project(db, project)
