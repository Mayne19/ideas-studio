import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.utils import calculate_word_count
from app.dependencies.auth import get_current_user, require_project_role
from app.models.user import User
from app.models.project import Project
from app.models.article import Article
from app.models.project_member import ProjectMember
from app.schemas.ideas import (
    IdeaGenerateRequest, IdeaGenerateResponse,
    IdeaRejectRequest, IdeaPriorityRequest,
    LaunchRequest,
)
from app.services.idea_engine import generate_idea
from app.services.writing_engine import start_writing_from_idea, _mock_content_from_outline, _MOCK_OUTLINE
from app.services.log_service import log_step
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider

router = APIRouter(tags=["ideas"])

_IDEA_STATUSES = frozenset({"idea_proposed", "idea_priority"})
_WRITABLE_STATUSES = frozenset({"idea_proposed", "idea_priority", "outline_ready", "failed", "update_recommended"})
_RERUN_STATUSES = frozenset({"idea_proposed", "idea_priority", "outline_ready", "failed", "draft_ready", "correction_needed", "update_recommended"})


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_article_or_404(article_id: str, db: Session) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _check_role(db: Session, user_id: str, project_id: str, allowed_roles: tuple) -> ProjectMember:
    member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status == "active",
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied: not a project member")
    if member.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Required role(s): {', '.join(allowed_roles)}")
    return member


def _idea_response(article: Article) -> IdeaGenerateResponse:
    return IdeaGenerateResponse(
        id=article.id,
        title=article.title,
        keyword=article.keyword,
        angle=article.angle,
        search_intent=article.search_intent,
        audience=article.audience,
        opportunity_score=article.opportunity_score,
        status=article.status,
    )


def _generation_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProviderUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, GenerationFailedError):
        return HTTPException(status_code=502, detail=str(exc))
    raise exc


@router.post("/projects/{project_id}/ideas/generate", response_model=IdeaGenerateResponse)
def generate_idea_route(
    project_id: str,
    body: IdeaGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor", "writer")),
):
    project = _get_project_or_404(project_id, db)
    try:
        llm = get_llm_provider()
        search = get_search_provider()
        article = generate_idea(
            db=db,
            project_id=project_id,
            project_audience=project.audience,
            project_language=project.language,
            llm=llm,
            search=search,
            context_hint=body.context_hint,
            preferred_title=body.preferred_title,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc
    if article is None:
        raise HTTPException(status_code=409, detail="Idea could not be generated (duplicate keyword or LLM failure)")
    db.commit()
    db.refresh(article)
    return _idea_response(article)


@router.post("/articles/{article_id}/start-writing", response_model=IdeaGenerateResponse)
def start_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor", "writer"))
    if article.status not in _WRITABLE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot start writing from status '{article.status}'")
    try:
        llm = get_llm_provider()
        article = start_writing_from_idea(db=db, article=article, llm=llm)
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc
    db.commit()
    db.refresh(article)
    return _idea_response(article)


@router.post("/articles/{article_id}/reject")
def reject_idea_route(
    article_id: str,
    body: IdeaRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status not in _IDEA_STATUSES:
        raise HTTPException(status_code=400, detail="Only ideas can be rejected")
    article.status = "idea_rejected"
    article.rejection_reason = body.rejection_reason
    article.rejection_note = body.rejection_note
    article.updated_at = datetime.now(timezone.utc)
    log_step(db, article.project_id, f"Idée rejetée : {article.title}", level="info", step="reject", article_id=article.id)
    db.commit()
    return {"status": "rejected"}


@router.post("/articles/{article_id}/priority")
def set_priority_route(
    article_id: str,
    body: IdeaPriorityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    article.priority = body.priority
    if article.status == "idea_proposed":
        article.status = "idea_priority"
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"priority": article.priority, "status": article.status}


@router.post("/articles/{article_id}/manual-draft", response_model=IdeaGenerateResponse)
def manual_draft_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor", "writer"))
    if article.status not in _IDEA_STATUSES:
        raise HTTPException(status_code=400, detail="Only ideas can be converted to a manual draft")

    # Build skeleton from outline_json if available, else use default
    if article.outline_json:
        try:
            outline = json.loads(article.outline_json)
        except Exception:
            outline = _MOCK_OUTLINE
    else:
        outline = _MOCK_OUTLINE
        article.outline_json = json.dumps(outline)

    content = _mock_content_from_outline(article.title, article.keyword or "", outline)
    article.content = content
    article.word_count = calculate_word_count(content)
    article.status = "draft_ready"
    article.updated_at = datetime.now(timezone.utc)

    log_step(db, article.project_id, f"Brouillon manuel créé : {article.title}", level="info", step="manual_draft", article_id=article.id)
    db.commit()
    db.refresh(article)
    return _idea_response(article)


@router.post("/articles/{article_id}/rerun", response_model=IdeaGenerateResponse)
def rerun_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor", "writer"))
    if article.status not in _RERUN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot rerun from status '{article.status}'")
    try:
        llm = get_llm_provider()
        article = start_writing_from_idea(db=db, article=article, llm=llm)
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc
    db.commit()
    db.refresh(article)
    return _idea_response(article)


@router.post("/projects/{project_id}/launch")
def launch_project_route(
    project_id: str,
    body: LaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin")),
):
    project = _get_project_or_404(project_id, db)
    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    from app.core.config import settings
    generated = []
    for _ in range(settings.IDEAS_PER_DAY):
        if body.dry_run:
            break
        try:
            article = generate_idea(
                db=db,
                project_id=project_id,
                project_audience=project.audience,
                project_language=project.language,
                llm=llm,
                search=search,
            )
        except (ProviderUnavailableError, GenerationFailedError) as exc:
            raise _generation_http_error(exc) from exc
        if article:
            if body.mode == "full_article":
                try:
                    article = start_writing_from_idea(db=db, article=article, llm=llm)
                except (ProviderUnavailableError, GenerationFailedError) as exc:
                    raise _generation_http_error(exc) from exc
            generated.append(article.id)

    if not body.dry_run:
        db.commit()

    return {
        "project_id": project_id,
        "mode": body.mode,
        "dry_run": body.dry_run,
        "ideas_generated": len(generated),
        "article_ids": generated,
    }
