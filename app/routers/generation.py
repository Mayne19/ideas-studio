import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_project_role
from app.models.core import Project
from app.models.content import Article
from app.models.reference import ArticleStatus
from app.services.article_service import primary_keyword, to_public
from app.services.idea_engine import generate_idea
from app.services.seo.seo_generation_orchestrator import generate_full_article
from app.services.seo.artifacts import get_latest_artifact, get_all_latest_artifacts
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider
from app.services.seo.category_strategy_service import compute_category_strategy_dict
from app.services.seo.idea_discovery_service import discover_ideas

logger = logging.getLogger(__name__)

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
    use_orchestrator: bool = True


class GenerateArticleResponse(BaseModel):
    id: str
    title: str
    keyword: str | None
    status: int
    word_count: int
    provider_name: str | None = None
    model_name: str | None = None
    has_generation_report: bool = False


class AutoGenerateIdeasRequest(BaseModel):
    count: int = 3
    context_hint: str | None = None


class AutoGenerateIdeasResponse(BaseModel):
    ideas: list[dict]
    generated: int


class IdeaDiscoverRequest(BaseModel):
    count: int = 5
    context_hint: str | None = None


class IdeaDiscoverResponse(BaseModel):
    ideas: list[dict]
    generated: int
    strategy: dict


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
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)
    profile = project.active_editorial_profile

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    logger.info(
        "generation_start provider=%s model=%s is_mock=%s project=%s",
        llm.provider_name, llm.model_name, llm.is_mock, project_id,
    )

    try:
        from app.services.agents.agent_router import get_agent_router
        article = generate_full_article(
            db=db,
            project_id=project_id,
            llm=llm,
            search=search,
            agent_router=get_agent_router(db=db),
            preferred_title=body.preferred_title,
            keyword=body.keyword,
            category_id=body.category_id,
            audience=body.audience or (profile.audience if profile else None),
            angle=body.angle,
            search_intent=body.search_intent,
            context_hint=body.context_hint,
            include_faq=body.include_faq,
            include_callouts=body.include_callouts,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    db.commit()
    db.refresh(article)

    revision = article.current_revision
    return GenerateArticleResponse(
        id=article.id,
        title=revision.title if revision else "",
        keyword=primary_keyword(db, article.id),
        status=article.status_reason_id,
        word_count=revision.word_count if revision else 0,
        provider_name=llm.provider_name,
        model_name=llm.model_name,
        has_generation_report=get_latest_artifact(db, article.id, "generation_report") is not None,
    )


@router.get("/projects/{project_id}/articles/{article_id}/generation-report")
def get_generation_report(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "designer", "viewer")),
):
    article = db.get(Article, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    return get_latest_artifact(db, article_id, "generation_report") or {"error": "No generation report available"}


@router.get("/projects/{project_id}/articles/{article_id}/seo-workflow")
def get_seo_workflow(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "designer", "viewer")),
):
    article = db.get(Article, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    return get_all_latest_artifacts(db, article_id)


@router.post("/projects/{project_id}/ideas/auto-generate", response_model=AutoGenerateIdeasResponse)
def auto_generate_ideas_route(
    project_id: str,
    body: AutoGenerateIdeasRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)
    profile = project.active_editorial_profile

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    logger.info(
        "auto_ideas_start provider=%s model=%s is_mock=%s project=%s count=%d",
        llm.provider_name, llm.model_name, llm.is_mock, project_id, body.count,
    )

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
                project_audience=profile.audience if profile else None,
                project_language=project.locale.split("-")[0] if project.locale else "fr",
                llm=llm,
                search=search,
                context_hint=context,
            )
            if article:
                revision = article.current_revision
                generated.append({
                    "id": article.id,
                    "title": revision.title if revision else "",
                    "keyword": primary_keyword(db, article.id),
                    "search_intent": article.search_intent,
                    "opportunity_score": float(article.opportunity_score) if article.opportunity_score is not None else None,
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


@router.post("/projects/{project_id}/ideas/discover", response_model=IdeaDiscoverResponse)
def discover_ideas_route(
    project_id: str,
    body: IdeaDiscoverRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)
    profile = project.active_editorial_profile

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    strategy = compute_category_strategy_dict(db, project_id)
    ideas = discover_ideas(
        db=db,
        project_id=project_id,
        llm=llm,
        search=search,
        count=body.count,
        context_hint=body.context_hint,
        project_audience=profile.audience if profile else None,
        project_language=project.locale.split("-")[0] if project.locale else "fr",
        category_strategy=strategy,
    )

    return IdeaDiscoverResponse(
        ideas=ideas,
        generated=len(ideas),
        strategy=strategy,
    )


class MonthlyPlanRequest(BaseModel):
    force: bool = False
    generation_day: int | None = None


@router.post("/projects/{project_id}/planning/monthly")
def generate_monthly_plan_route(
    project_id: str,
    body: MonthlyPlanRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin")),
):
    from app.services.monthly_planning import generate_monthly_plan
    from app.services.agents.agent_router import get_agent_router

    project = _get_project_or_404(project_id, db)
    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    agent_router = get_agent_router(db=db)
    result = generate_monthly_plan(
        db=db,
        project_id=project_id,
        llm=llm,
        search=search,
        agent_router=agent_router,
        generation_day=body.generation_day or 27,
        force=body.force,
    )
    db.commit()
    return result
