from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_project_member
from app.models.core import Project
from app.schemas.editorial_setup import EditorialSetupResponse
from app.services.editorial_setup_service import generate_setup_suggestions

router = APIRouter(prefix="/projects", tags=["editorial_setup"])


@router.post("/{project_id}/editorial-setup/suggest", response_model=EditorialSetupResponse)
def suggest_editorial_setup(
    project_id: str,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.domain:
        raise HTTPException(
            status_code=400,
            detail="Aucun domaine configuré. Renseignez d'abord le domaine du site dans les paramètres.",
        )
    return generate_setup_suggestions(db, project)
