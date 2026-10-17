"""Routes du nouveau parcours éditorial, sans basculer l'ancien pipeline."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_project_role
from app.models.ai import Pipeline
from app.models.content import Article
from app.models.reference import ArticleStatus, set_article_status
from app.services.editorial_workflow_service import (
    EditorialStatus,
    deposit_markdown,
    request_writing,
    schedule_for_publication,
    validate_for_publication,
    workflow_article_details,
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
    category_id: str | None = None
    category_name: str | None = None
    keyword: str | None = None
    duplicate: bool = False
    score: int | None = None
    checks: list[dict] = []
    alerts: list[str] = []
    fiche: dict | None = None
    planned_write_at: datetime | None = None
    cost_usd: float | None = None
    error: str | None = None


class ValidationResponse(BaseModel):
    article: WorkflowArticleResponse
    passed: bool
    checks: list[dict]
    scheduled_for: datetime | None = None
    global_score: int | None = None
    min_publish_score: int | None = None


def _article_or_404(db: Session, project_id: str, article_id: str) -> Article:
    article = db.get(Article, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _article_response(db: Session, article: Article) -> WorkflowArticleResponse:
    revision = article.current_revision
    details = workflow_article_details(db, article)
    return WorkflowArticleResponse(
        id=article.id,
        title=revision.title if revision else "",
        slug=article.slug,
        status=workflow_status(article),
        scheduled_for=article.scheduled_for,
        published_at=article.published_at,
        updated_at=article.updated_at,
        **details,
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
        _article_response(db, article)
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
    return (
        _list_articles(db, project_id, EditorialStatus.IDEA)
        + _list_articles(db, project_id, EditorialStatus.WRITING)
        + _list_articles(db, project_id, EditorialStatus.ERROR)
    )


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
    return _article_response(db, request_writing(db, article))


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
    return _article_response(db, result)


@router.post("/articles/{article_id}/validate", response_model=ValidationResponse)
def validate_article(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    pipeline = db.get(Pipeline, project_id)
    schedule = pipeline.schedule if pipeline else {}
    start_hour = int(schedule.get("publish_hour_start", 8))
    scheduled_for = article.scheduled_for or (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=start_hour, minute=0, second=0, microsecond=0,
    )
    report = schedule_for_publication(db, article, scheduled_for)
    return ValidationResponse(article=_article_response(db, article), **report)


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
    return ValidationResponse(article=_article_response(db, article), **report)


class WorkflowCommentRequest(BaseModel):
    comment: str = Field(default="", max_length=2000)


@router.post("/articles/{article_id}/return-to-writing", response_model=WorkflowArticleResponse)
def return_article_to_writing(
    project_id: str,
    article_id: str,
    body: WorkflowCommentRequest,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    return _article_response(db, request_writing(db, article, comment=body.comment.strip() or None))


@router.post("/articles/{article_id}/reject", response_model=WorkflowArticleResponse)
def reject_workflow_article(
    project_id: str,
    article_id: str,
    body: WorkflowCommentRequest,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    article = _article_or_404(db, project_id, article_id)
    set_article_status(article, ArticleStatus.IDEA_REJECTED)
    article.rejection_note = body.comment.strip() or None
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return _article_response(db, article)
