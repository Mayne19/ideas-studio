import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_project_role
from app.models.core import Project
from app.models.content import Article
from app.services.article_service import primary_keyword
from app.services.idea_engine import generate_idea
from app.services.generation_job_service import (
    create_generation_job,
    get_generation_job,
    job_to_dict,
    list_generation_jobs,
    submit_generation_job,
)
from app.services.editorial_workflow_service import create_workflow_idea, request_writing
from app.services.seo.artifacts import get_latest_artifact, get_all_latest_artifacts
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider
from app.services.seo.category_strategy_service import compute_category_strategy_dict
from app.services.seo.idea_discovery_service import discover_ideas
from app.services.pipeline_service import cap_ideas_count

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
    # Savoir de terrain du fondateur (prix réels, cas client, erreurs vues) :
    # intégré en priorité par le rédacteur, source de gain d'information.
    expert_notes: str | None = Field(default=None, max_length=4000)
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
    # Absent = plafond du projet (Paramètres → Pipeline → Idées par lancement) ;
    # toute valeur supérieure est ramenée à ce plafond.
    count: int | None = None
    context_hint: str | None = None


class AutoGenerateIdeasResponse(BaseModel):
    ideas: list[dict]
    generated: int


class IdeaDiscoverRequest(BaseModel):
    # Même plafond que l'auto-génération : chaque idée coûte un appel LLM.
    count: int | None = None
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


class GenerationJobResponse(BaseModel):
    id: str
    project_id: str
    status: str
    article_id: str | None = None
    current_step: str | None = None
    steps_completed: int = 0
    error: str | None = None
    title: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@router.post(
    "/projects/{project_id}/articles/generate",
    status_code=202,
    response_model=GenerationJobResponse | GenerateArticleResponse,
)
def generate_article_route(
    project_id: str,
    body: GenerateArticleRequest,
    response: Response,
    sync: bool = Query(False, description="Ancien mode synchrone (scripts uniquement : coupé à 300 s par le proxy)."),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    """Crée un job de génération exécuté en tâche de fond et répond 202 avec
    son id ; suivre l'avancement via GET /projects/{id}/generation-jobs/{job_id}."""
    _get_project_or_404(project_id, db)
    if sync:
        response.status_code = 200
        return _generate_article_sync(project_id, body, db)

    job = create_generation_job(
        db, project_id, getattr(current_user, "id", None),
        body.model_dump(exclude={"use_orchestrator"}),
    )
    db.commit()
    submit_generation_job(job.id, project_id)
    logger.info("generation_job_queued job=%s project=%s", job.id, project_id)
    return GenerationJobResponse(**job_to_dict(job))


@router.get("/projects/{project_id}/generation-jobs", response_model=list[GenerationJobResponse])
def list_generation_jobs_route(
    project_id: str,
    limit: int = Query(10, ge=1, le=50),
    active: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "designer", "viewer")),
):
    return [GenerationJobResponse(**job_to_dict(job)) for job in list_generation_jobs(db, project_id, limit, active)]


@router.get("/projects/{project_id}/generation-jobs/{job_id}", response_model=GenerationJobResponse)
def get_generation_job_route(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "designer", "viewer")),
):
    job = get_generation_job(db, project_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return GenerationJobResponse(**job_to_dict(job))


def _generate_article_sync(project_id: str, body: GenerateArticleRequest, db: Session) -> GenerateArticleResponse:
    _get_project_or_404(project_id, db)
    article = create_workflow_idea(
        db=db,
        project_id=project_id,
        title=body.preferred_title or body.keyword or "Nouvelle idée",
        keyword=body.keyword,
        category_id=body.category_id,
        audience=body.audience,
        angle=body.angle,
        search_intent=body.search_intent,
        context_hint=body.context_hint,
    )
    request_writing(db, article)
    db.commit()
    db.refresh(article)

    revision = article.current_revision
    return GenerateArticleResponse(
        id=article.id,
        title=revision.title if revision else "",
        keyword=primary_keyword(db, article.id),
        status=article.status_reason_id,
        word_count=revision.word_count if revision else 0,
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
        search = get_search_provider(project_id)
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    count = cap_ideas_count(db, project_id, body.count)
    logger.info(
        "auto_ideas_start provider=%s model=%s is_mock=%s project=%s count=%d requested=%s",
        llm.provider_name, llm.model_name, llm.is_mock, project_id, count, body.count,
    )

    generated = []
    errors = []

    for i in range(count):
        try:
            context = body.context_hint
            if context:
                context += f" (proposition {i + 1}/{count})"
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
        search = get_search_provider(project_id)
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    strategy = compute_category_strategy_dict(db, project_id)
    ideas = discover_ideas(
        db=db,
        project_id=project_id,
        llm=llm,
        search=search,
        count=cap_ideas_count(db, project_id, body.count),
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
        search = get_search_provider(project_id)
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
