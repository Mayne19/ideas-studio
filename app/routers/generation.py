import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_project_role
from app.models.project import Project
from app.models.user import User
from app.services.idea_engine import generate_idea
from app.services.writing_engine import start_writing_from_idea
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider

router = APIRouter(tags=["generation"])


class GenerateArticleRequest(BaseModel):
    preferred_title: str | None = None
    keyword: str | None = None
    category_id: str | None = None
    audience: str | None = None
    angle: str | None = None
    search_intent: str | None = None
    context_hint: str | None = None
    include_faq: bool | None = None
    include_callouts: bool | None = None


class GenerateArticleResponse(BaseModel):
    id: str
    title: str
    keyword: str | None
    status: str
    word_count: int
    provider_name: str | None = None
    model_name: str | None = None


class AutoGenerateIdeasRequest(BaseModel):
    count: int = 3
    context_hint: str | None = None


class AutoGenerateIdeasResponse(BaseModel):
    ideas: list[dict]
    generated: int


def _generation_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProviderUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, GenerationFailedError):
        return HTTPException(status_code=502, detail=str(exc))
    raise exc


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/articles/generate", response_model=GenerateArticleResponse)
def generate_article_route(
    project_id: str,
    body: GenerateArticleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "writer")),
):
    project = _get_project_or_404(project_id, db)

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    # Step 1: generate idea
    try:
        article = generate_idea(
            db=db,
            project_id=project_id,
            project_audience=project.audience,
            project_language=project.language,
            llm=llm,
            search=search,
            context_hint=body.context_hint,
            preferred_title=body.preferred_title,
            keyword=body.keyword,
            category_id=body.category_id,
            audience=body.audience,
            angle=body.angle,
            search_intent=body.search_intent,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    if article is None:
        raise HTTPException(status_code=409, detail="L'idée n'a pas pu être générée (keyword déjà actif ou échec LLM).")

    # Step 2: full article generation
    try:
        article = start_writing_from_idea(
            db=db,
            article=article,
            llm=llm,
            preferred_title=body.preferred_title,
            keyword=body.keyword,
            audience=body.audience,
            angle=body.angle,
            search_intent=body.search_intent,
            include_faq=body.include_faq,
            include_callouts=body.include_callouts,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    db.commit()
    db.refresh(article)

    return GenerateArticleResponse(
        id=article.id,
        title=article.title,
        keyword=article.keyword,
        status=article.status,
        word_count=article.word_count,
        provider_name=llm.provider_name,
        model_name=llm.model_name,
    )


@router.post("/projects/{project_id}/ideas/auto-generate", response_model=AutoGenerateIdeasResponse)
def auto_generate_ideas_route(
    project_id: str,
    body: AutoGenerateIdeasRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    generated = []
    errors = []

    for i in range(body.count):
        try:
            context = body.context_hint
            if context:
                context += f" (proposition {i + 1}/{body.count})"
            article = generate_idea(
                db=db,
                project_id=project_id,
                project_audience=project.audience,
                project_language=project.language,
                llm=llm,
                search=search,
                context_hint=context,
            )
            if article:
                generated.append({
                    "id": article.id,
                    "title": article.title,
                    "keyword": article.keyword,
                    "angle": article.angle,
                    "search_intent": article.search_intent,
                    "audience": article.audience,
                    "opportunity_score": article.opportunity_score,
                })
        except (ProviderUnavailableError, GenerationFailedError) as exc:
            errors.append(str(exc))

    db.commit()

    if not generated and errors:
        raise HTTPException(status_code=503, detail=errors[0])

    return AutoGenerateIdeasResponse(
        ideas=generated,
        generated=len(generated),
    )
