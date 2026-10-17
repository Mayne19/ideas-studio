"""Routes du nouveau parcours éditorial, sans basculer l'ancien pipeline."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_project_role
from app.models.content import Article
from app.services.editorial_workflow_service import (
    EditorialStatus,
    deposit_markdown,
    request_writing,
    schedule_for_publication,
    validate_for_publication,
    workflow_status,
)


router = APIRouter(
    prefix="/projects/{project_id}/editorial-workflow",
    tags=["editorial_workflow"],
)

_READ_ROLES = ("owner", "admin", "editor", "viewer")
_WRITE_ROLES = ("owner", "admin", "editor")


class WriterDepositRequest(BaseModel):
    markdown: str = Field(min_length=1)
    fiche: dict | None = None
    title: str | None = None
    fiche_error: str = ""


class ScheduleRequest(BaseModel):
    scheduled_for: datetime


class WorkflowArticleResponse(BaseModel):
    id: str
    title: str
    slug: str
    status: EditorialStatus | None
    scheduled_for: datetime | None
    published_at: datetime | None
    updated_at: datetime


class ValidationResponse(BaseModel):
    article: WorkflowArticleResponse
    passed: bool
    checks: list[dict]
    scheduled_for: datetime | None = None


def _article_or_404(db: Session, project_id: str, article_id: str) -> Article:
    article = db.get(Article, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _article_response(article: Article) -> WorkflowArticleResponse:
    revision = article.current_revision
    return WorkflowArticleResponse(
        id=article.id,
        title=revision.title if revision else "",
        slug=article.slug,
        status=workflow_status(article),
        scheduled_for=article.scheduled_for,
        published_at=article.published_at,
        updated_at=article.updated_at,
    )


def _list_articles(
    db: Session,
    project_id: str,
    status: EditorialStatus | None = None,
) -> list[WorkflowArticleResponse]:
    articles = db.execute(
        select(Article)
        .where(Article.project_id == project_id)
        .order_by(Article.updated_at.desc())
    ).scalars().all()
    return [
        _article_response(article)
        for article in articles
        if status is None or workflow_status(article) == status
    ]


@router.get("/articles", response_model=list[WorkflowArticleResponse])
def list_workflow_articles(
    project_id: str,
    status: EditorialStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_READ_ROLES)),
):
    return _list_articles(db, project_id, status)


@router.get("/writing-queue", response_model=list[WorkflowArticleResponse])
def list_writing_queue(
    project_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    return _list_articles(db, project_id, EditorialStatus.IDEA) + _list_articles(db, project_id, EditorialStatus.WRITING)


@router.get("/updates", response_model=list[WorkflowArticleResponse])
def list_updates(
    project_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_READ_ROLES)),
):
    return _list_articles(db, project_id, EditorialStatus.UPDATE)


@router.get("/calendar", response_model=list[WorkflowArticleResponse])
def publication_calendar(
    project_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_READ_ROLES)),
):
    return _list_articles(db, project_id, EditorialStatus.SCHEDULED)


@router.post("/articles/{article_id}/request-writing", response_model=WorkflowArticleResponse)
def request_article_writing(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    return _article_response(request_writing(db, article))


@router.post("/articles/{article_id}/deposit", response_model=WorkflowArticleResponse)
def deposit_writer_article(
    project_id: str,
    article_id: str,
    body: WriterDepositRequest,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    try:
        result = deposit_markdown(
            db,
            article,
            body.markdown,
            body.fiche,
            title=body.title,
            fiche_error=body.fiche_error,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _article_response(result)


@router.post("/articles/{article_id}/validate", response_model=ValidationResponse)
def validate_article(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    report = validate_for_publication(db, article)
    return ValidationResponse(article=_article_response(article), **report)


@router.post("/articles/{article_id}/schedule", response_model=ValidationResponse)
def schedule_article(
    project_id: str,
    article_id: str,
    body: ScheduleRequest,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    report = schedule_for_publication(db, article, body.scheduled_for)
    return ValidationResponse(article=_article_response(article), **report)
