"""Routes du rédacteur local (phase 3 de la refonte) : file des sujets à
rédiger, articles du site pour le maillage interne, rapport du rédacteur.
Le dépôt de l'article se fait par la route de dépôt du parcours éditorial."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_project_role
from app.models.content import Article
from app.services.local_writer_service import record_writer_report, site_articles, writing_jobs

router = APIRouter(prefix="/projects/{project_id}/local-writer", tags=["local_writer"])

_WRITE_ROLES = ("owner", "admin", "editor")


class WriterJob(BaseModel):
    article_id: str
    subject: str
    keyword: str | None = None
    context: str | None = None
    audience: str | None = None
    angle: str | None = None
    comment: str | None = None


class SiteArticle(BaseModel):
    titre: str
    url: str
    resume: str


class WriterReport(BaseModel):
    cost_usd: float | None = None
    tokens: dict | None = None
    duration_s: float | None = None
    turns: int | None = None
    error: str | None = None
    checks: list[dict] | None = None


@router.get("/jobs", response_model=list[WriterJob])
def list_jobs(project_id: str, db: Session = Depends(get_db),
              _member=Depends(require_project_role(*_WRITE_ROLES))):
    return writing_jobs(db, project_id)


@router.get("/site-articles", response_model=list[SiteArticle])
def list_site_articles(project_id: str, db: Session = Depends(get_db),
                       _member=Depends(require_project_role(*_WRITE_ROLES))):
    return site_articles(db, project_id)


@router.post("/articles/{article_id}/report")
def post_writer_report(project_id: str, article_id: str, body: WriterReport, db: Session = Depends(get_db),
                       _member=Depends(require_project_role(*_WRITE_ROLES))):
    article = db.get(Article, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    return record_writer_report(db, article, body.model_dump(exclude_none=True))
