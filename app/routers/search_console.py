from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_project_member
from app.models.project_member import ProjectMember
from app.models.project import Project

router = APIRouter(prefix="/projects/{project_id}/search-console", tags=["search_console"])


@router.get("/status")
def search_console_status(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return {
        "connected": False,
        "provider": "google_search_console",
        "message": "Google Search Console nécessite une configuration OAuth. Consultez la documentation pour connecter votre compte Google.",
        "docs_url": "https://developers.google.com/webmaster-tools/search-console-api",
    }


@router.get("/keywords")
def search_console_keywords(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return {
        "connected": False,
        "keywords": [],
        "message": "Google Search Console non connecté. Configurez l'intégration via OAuth pour accéder aux données de recherche.",
    }


@router.get("/pages")
def search_console_pages(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return {
        "connected": False,
        "pages": [],
        "message": "Google Search Console non connecté.",
    }


@router.get("/performance")
def search_console_performance(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return {
        "connected": False,
        "impressions": 0,
        "clicks": 0,
        "ctr": 0.0,
        "position": 0.0,
        "message": "Google Search Console non connecté.",
    }
