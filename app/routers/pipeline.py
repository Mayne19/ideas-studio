import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_project_member, require_project_role
from app.models.project_member import ProjectMember
from app.schemas.pipeline import PipelineSettingsUpdate, PipelineSettingsPublic, PipelineLogPublic
from app.services import pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])

_MANAGE_ROLES = frozenset({"owner", "admin"})


@router.get("/projects/{project_id}/pipeline", response_model=PipelineSettingsPublic)
def get_pipeline_settings(
    project_id: str,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return pipeline_service.get_pipeline(db, project_id)


@router.patch("/projects/{project_id}/pipeline", response_model=PipelineSettingsPublic)
def update_pipeline_settings(
    project_id: str,
    data: PipelineSettingsUpdate,
    _member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    return pipeline_service.update_pipeline(db, project_id, data)


@router.post("/projects/{project_id}/pipeline/run")
def trigger_pipeline_run(
    project_id: str,
    _member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    return pipeline_service.run_pipeline(db, project_id)


@router.get("/projects/{project_id}/pipeline/logs", response_model=list[PipelineLogPublic])
def get_pipeline_logs(
    project_id: str,
    limit: int = 20,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return pipeline_service.list_pipeline_logs(db, project_id, limit=limit)
