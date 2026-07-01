import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_project_role
from app.models.project import Project
from app.models.article import Article
from app.models.user import User
from app.services.idea_engine import generate_idea
from app.services.writing_engine import start_writing_from_idea
from app.services.seo.seo_generation_orchestrator import generate_full_article
from app.services.seo.helpers import safe_json_dump, safe_json_load
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider
from app.services.seo.project_context_service import build_project_context_dict
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
    status: str
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
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    logger.info(
        "generation_start provider=%s model=%s is_mock=%s project=%s orchestrator=%s",
        llm.provider_name, llm.model_name, llm.is_mock, project_id, body.use_orchestrator,
    )

    if body.use_orchestrator:
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
                audience=body.audience or project.audience,
                angle=body.angle,
                search_intent=body.search_intent,
                context_hint=body.context_hint,
                include_faq=body.include_faq,
                include_callouts=body.include_callouts,
            )
        except (ProviderUnavailableError, GenerationFailedError) as exc:
            raise _generation_http_error(exc) from exc
    else:
        # Legacy mode: idea + writing
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
            raise HTTPException(status_code=409, detail="L'idée n'a pas pu être générée (keyword déjà actif ou échec LLM).")

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
        has_generation_report=article.generation_report_json is not None,
    )


@router.get("/projects/{project_id}/articles/{article_id}/generation-report")
def get_generation_report(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = db.query(Article).filter(Article.id == article_id, Article.project_id == project_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article.generation_report_json or {"error": "No generation report available"}


@router.get("/projects/{project_id}/articles/{article_id}/seo-workflow")
def get_seo_workflow(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = db.query(Article).filter(Article.id == article_id, Article.project_id == project_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "project_context_json": article.project_context_json,
        "category_strategy_json": article.category_strategy_json,
        "idea_discovery_json": article.idea_discovery_json,
        "intent_analysis_json": article.intent_analysis_json,
        "research_brief_json": article.research_brief_json,
        "keyword_brief_json": article.keyword_brief_json,
        "cannibalization_check_json": article.cannibalization_check_json,
        "editorial_angle_json": article.editorial_angle_json,
        "outline_json": safe_json_load(article.outline_json) if article.outline_json else None,
        "image_plan_json": article.image_plan_json,
        "image_sources_json": article.image_sources_json,
        "callout_plan_json": article.callout_plan_json,
        "faq_json": safe_json_load(article.faq_json) if article.faq_json else None,
        "internal_links_json": safe_json_load(article.internal_links_json) if article.internal_links_json else None,
        "external_links_json": safe_json_load(article.external_links_json) if article.external_links_json else None,
        "language_quality_report_json": article.language_quality_report_json,
        "originality_report_json": article.originality_report_json,
        "humanization_report_json": article.humanization_report_json,
        "eeat_checklist_json": article.eeat_checklist_json,
        "editorial_quality_report_json": article.editorial_quality_report_json,
        "seo_final_checklist_json": article.seo_final_checklist_json,
        "seo_review_json": article.seo_review_json,
        "generation_report_json": article.generation_report_json,
        "sources_json": article.sources_json,
    }


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


@router.post("/projects/{project_id}/ideas/discover", response_model=IdeaDiscoverResponse)
def discover_ideas_route(
    project_id: str,
    body: IdeaDiscoverRequest,
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

    strategy = compute_category_strategy_dict(db, project_id)
    ideas = discover_ideas(
        db=db,
        project_id=project_id,
        llm=llm,
        search=search,
        count=body.count,
        context_hint=body.context_hint,
        project_audience=project.audience,
        project_language=project.language,
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
    current_user: User = Depends(get_current_user),
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
