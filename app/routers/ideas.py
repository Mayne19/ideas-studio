import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.dependencies.auth import get_current_user, require_project_role, role_code
from app.models.core import Project, ProjectMember, User
from app.models.content import Article
from app.models.reference import ArticleStatus, MembershipStatus, RunStatus, set_article_status, set_run_status
from app.schemas.ideas import (
    IdeaGenerateRequest, IdeaGenerateResponse,
    IdeaRejectRequest, IdeaPriorityRequest,
    LaunchRequest, BulkDeleteRequest, BulkDeleteResponse,
)
from app.services.idea_engine import generate_idea
from app.services.article_service import primary_keyword
from app.services.log_service import log_step
from app.services.production_queue import send_to_production, process_queue, get_queue_summary
from app.services.providers.llm_provider import (
    GenerationFailedError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services.providers.search_provider import get_search_provider

router = APIRouter(tags=["ideas"])

_IDEA_STATUSES = frozenset({ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY})
_DELETABLE_IDEA_STATUSES = frozenset({ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY, ArticleStatus.IDEA_REJECTED})
_WRITABLE_STATUSES = frozenset({ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY, ArticleStatus.OUTLINE_READY, ArticleStatus.FAILED, ArticleStatus.UPDATE_RECOMMENDED})
_RERUN_STATUSES = frozenset({
    ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY, ArticleStatus.OUTLINE_READY, ArticleStatus.FAILED,
    ArticleStatus.DRAFT_READY, ArticleStatus.CORRECTION_NEEDED, ArticleStatus.UPDATE_RECOMMENDED,
})


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
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied: not a project member")
    if role_code(member.role_id) not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Required role(s): {', '.join(allowed_roles)}")
    return member


def _idea_response(db: Session, article: Article, provider=None) -> IdeaGenerateResponse:
    revision = article.current_revision
    return IdeaGenerateResponse(
        id=article.id,
        title=revision.title if revision else "",
        keyword=primary_keyword(db, article.id),
        category_id=article.category_id,
        search_intent=article.search_intent,
        opportunity_score=float(article.opportunity_score) if article.opportunity_score is not None else None,
        status=article.status_reason_id,
        provider_name=getattr(provider, "provider_name", None),
        model_name=getattr(provider, "model_name", None),
    )


def _generation_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProviderUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, GenerationFailedError):
        return HTTPException(status_code=502, detail=str(exc))
    raise exc


def _idea_delete_refusal(article: Article) -> str | None:
    if article.status_reason_id in (ArticleStatus.PUBLISHED, ArticleStatus.SCHEDULED) or article.published_at is not None:
        return "Cet article est déjà publié ou planifié et ne peut pas être supprimé depuis la page Idées."
    if article.status_reason_id not in _DELETABLE_IDEA_STATUSES:
        return "Cette idée est déjà en production et ne peut pas être supprimée depuis la page Idées."
    return None


@router.post("/projects/{project_id}/ideas/generate", response_model=IdeaGenerateResponse)
def generate_idea_route(
    project_id: str,
    body: IdeaGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    project = _get_project_or_404(project_id, db)
    profile = project.active_editorial_profile
    try:
        llm = get_llm_provider()
        search = get_search_provider()
        logger.info(
            "generate_idea provider=%s model=%s is_mock=%s project=%s",
            llm.provider_name, llm.model_name, llm.is_mock, project_id,
        )
        article = generate_idea(
            db=db,
            project_id=project_id,
            project_audience=profile.audience if profile else None,
            project_language=project.locale.split("-")[0] if project.locale else "fr",
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
        raise HTTPException(status_code=409, detail="Idea could not be generated (duplicate keyword or LLM failure)")
    db.commit()
    db.refresh(article)
    return _idea_response(db, article, llm)


@router.post("/articles/{article_id}/start-writing", response_model=IdeaGenerateResponse)
def start_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor", "writer"))
    if article.status_reason_id not in _WRITABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de lancer la rédaction depuis le statut '{article.status_reason_id}'"
        )
    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except ProviderUnavailableError as exc:
        raise _generation_http_error(exc) from exc

    logger.info(
        "start_writing_orchestrator provider=%s model=%s article=%s",
        llm.provider_name, llm.model_name, article_id,
    )

    try:
        from app.services.seo.seo_generation_orchestrator import generate_full_article
        from app.services.agents.agent_router import get_agent_router

        project = db.get(Project, article.project_id)
        profile = project.active_editorial_profile if project else None
        revision = article.current_revision

        article = generate_full_article(
            db=db,
            project_id=article.project_id,
            llm=llm,
            search=search,
            agent_router=get_agent_router(db=db),
            preferred_title=revision.title if revision else None,
            keyword=primary_keyword(db, article_id),
            category_id=article.category_id,
            audience=profile.audience if profile else None,
            existing_article_id=article_id,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    db.commit()
    db.refresh(article)
    return _idea_response(db, article, llm)


@router.post("/articles/{article_id}/reject")
def reject_idea_route(
    article_id: str,
    body: IdeaRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status_reason_id not in _IDEA_STATUSES:
        raise HTTPException(status_code=400, detail="Only ideas can be rejected")
    title = article.current_revision.title if article.current_revision else ""
    set_article_status(article, ArticleStatus.IDEA_REJECTED)
    article.rejection_reason = body.rejection_reason
    article.rejection_note = body.rejection_note
    article.updated_at = datetime.now(timezone.utc)
    log_step(db, article.project_id, f"Idée rejetée : {title}", level="info", step="reject", article_id=article.id)

    # Auto-replacement: generate a new idea if this was part of monthly planning
    replacement = None
    from app.services.seo.artifacts import get_latest_artifact
    schedule = get_latest_artifact(db, article.id, "planning_schedule")
    if schedule:
        try:
            project = db.get(Project, article.project_id)
            profile = project.active_editorial_profile if project else None
            if project:
                llm = get_llm_provider()
                search = get_search_provider()
                replacement = generate_idea(
                    db=db,
                    project_id=article.project_id,
                    project_audience=profile.audience if profile else None,
                    project_language=project.locale.split("-")[0] if project.locale else "fr",
                    llm=llm,
                    search=search,
                    category_id=article.category_id,
                    keyword=primary_keyword(db, article.id),
                )
                if replacement:
                    from app.services.seo.artifacts import save_artifact
                    save_artifact(db, replacement.id, "planning_schedule", schedule)
                    replacement_title = replacement.current_revision.title if replacement.current_revision else ""
                    log_step(
                        db, article.project_id,
                        f"Idée de remplacement générée : {replacement_title}",
                        level="info", step="auto_replace", article_id=replacement.id,
                    )
        except Exception:
            logger.exception("Auto-replacement failed after rejection")

    db.commit()
    result = {"status": "rejected"}
    if replacement:
        result["replacement"] = {"id": replacement.id, "title": replacement.current_revision.title if replacement.current_revision else ""}
    return result


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
    if article.status_reason_id == ArticleStatus.IDEA_PROPOSED:
        set_article_status(article, ArticleStatus.IDEA_PRIORITY)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"priority": article.priority, "status": article.status_reason_id}


@router.post("/articles/{article_id}/manual-draft", response_model=IdeaGenerateResponse)
def manual_draft_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.utils import calculate_word_count
    from app.models.content import ArticleRevision
    from app.models.reference import RevisionSource

    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status_reason_id not in _IDEA_STATUSES:
        raise HTTPException(status_code=400, detail="Only ideas can be converted to a manual draft")

    mock_outline = [
        {"heading": "Introduction", "notes": "Présenter le sujet et son importance"},
        {"heading": "Développement", "notes": "Expliquer les concepts clés en détail avec des exemples concrets"},
        {"heading": "Bonnes pratiques", "notes": "Conseils pratiques et recommandations actionnables"},
        {"heading": "Conclusion", "notes": "Résumé des points clés et perspectives"},
    ]
    keyword = primary_keyword(db, article_id) or ""
    title = article.current_revision.title if article.current_revision else ""
    parts = [f"<h1>{title}</h1>"]
    for section in mock_outline:
        parts.append(f"<h2>{section['heading']}</h2>")
        parts.append(f"<p>{section['notes']}. Ce contenu est un exemple généré à titre indicatif. Remplacez-le par votre propre texte développé et original.</p>")
    parts.append(f"<p><em>Article optimisé pour le mot-clé : {keyword}</em></p>")
    content = "".join(parts)

    last_no = db.execute(
        select(ArticleRevision.revision_no)
        .where(ArticleRevision.article_id == article.id)
        .order_by(ArticleRevision.revision_no.desc())
        .limit(1)
    ).scalar_one_or_none() or 0
    revision = ArticleRevision(
        article_id=article.id,
        revision_no=last_no + 1,
        source=RevisionSource.HUMAN,
        title=title,
        body=content,
        word_count=calculate_word_count(content),
    )
    db.add(revision)
    db.flush()
    article.current_revision_id = revision.id
    set_article_status(article, ArticleStatus.DRAFT_READY)
    article.updated_at = datetime.now(timezone.utc)

    log_step(db, article.project_id, f"Brouillon manuel créé : {title}", level="info", step="manual_draft", article_id=article.id)
    db.commit()
    db.refresh(article)
    return _idea_response(db, article)


@router.post("/articles/{article_id}/rerun", response_model=IdeaGenerateResponse)
def rerun_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status_reason_id not in _RERUN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot rerun from status '{article.status_reason_id}'")
    try:
        llm = get_llm_provider()
        search = get_search_provider()
        logger.info(
            "rerun_writing provider=%s model=%s is_mock=%s article=%s",
            llm.provider_name, llm.model_name, llm.is_mock, article_id,
        )
        from app.services.seo.seo_generation_orchestrator import generate_full_article
        from app.services.agents.agent_router import get_agent_router

        article = generate_full_article(
            db=db,
            project_id=article.project_id,
            llm=llm,
            search=search,
            agent_router=get_agent_router(db=db),
            keyword=primary_keyword(db, article_id),
            category_id=article.category_id,
            existing_article_id=article_id,
        )
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc
    db.commit()
    db.refresh(article)
    return _idea_response(db, article, llm)


@router.post("/projects/{project_id}/launch")
def launch_project_route(
    project_id: str,
    body: LaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin")),
):
    project = _get_project_or_404(project_id, db)
    profile = project.active_editorial_profile

    if body.dry_run:
        return {
            "dry_run": True,
            "generated": 0,
            "ideas_generated": 0,
            "articles_created": 0,
            "total": 0,
            "message": "Mode dry-run activé. Aucune génération réelle effectuée.",
        }

    try:
        llm = get_llm_provider()
        search = get_search_provider()
    except (ProviderUnavailableError, GenerationFailedError) as exc:
        raise _generation_http_error(exc) from exc

    generated = []
    for _ in range(1):
        try:
            article = generate_idea(
                db=db,
                project_id=project_id,
                project_audience=profile.audience if profile else None,
                project_language=project.locale.split("-")[0] if project.locale else "fr",
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
        if article:
            if body.mode == "full_article":
                try:
                    from app.services.seo.seo_generation_orchestrator import generate_full_article
                    from app.services.agents.agent_router import get_agent_router
                    article = generate_full_article(
                        db=db,
                        project_id=project_id,
                        llm=llm,
                        search=search,
                        agent_router=get_agent_router(db=db),
                        keyword=body.keyword,
                        audience=body.audience,
                        angle=body.angle,
                        search_intent=body.search_intent,
                        include_faq=body.include_faq,
                        include_callouts=body.include_callouts,
                        existing_article_id=article.id,
                    )
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
        "provider_name": getattr(llm, "provider_name", None),
        "model_name": getattr(llm, "model_name", None),
    }


@router.post("/articles/{article_id}/send-to-production")
def send_to_production_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    result = send_to_production(db, article_id)
    if not result:
        raise HTTPException(status_code=400, detail="Article cannot be sent to production (invalid status)")
    db.commit()
    db.refresh(result)
    return {
        "id": result.id,
        "title": result.current_revision.title if result.current_revision else "",
        "status": result.status_reason_id,
    }


@router.post("/articles/{article_id}/cancel-writing")
def cancel_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Annule une rédaction : immédiat si en file/échec, au prochain checkpoint si en cours."""
    from app.models.ai import WorkflowRun

    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    title = article.current_revision.title if article.current_revision else ""

    if article.status_reason_id in (ArticleStatus.WRITING_REQUESTED, ArticleStatus.FAILED):
        set_article_status(article, ArticleStatus.IDEA_PROPOSED)
        article.updated_at = datetime.now(timezone.utc)
        log_step(
            db, article.project_id,
            f"Rédaction annulée (retour en idée) : {title}",
            level="info", step="writing_queue", article_id=article.id,
        )
        db.commit()
        db.refresh(article)
        return {"id": article.id, "status": article.status_reason_id, "cancelled": True}

    if article.status_reason_id == ArticleStatus.WRITING_IN_PROGRESS:
        run = db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.article_id == article.id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if run:
            run.cancel_requested = True
        article.updated_at = datetime.now(timezone.utc)
        log_step(
            db, article.project_id,
            f"Annulation demandée pour la rédaction en cours : {title}",
            level="info", step="writing_queue", article_id=article.id,
        )
        db.commit()
        return {"id": article.id, "status": article.status_reason_id, "cancelled": False, "cancel_requested": True}

    raise HTTPException(
        status_code=400,
        detail=f"Impossible d'annuler depuis le statut '{article.status_reason_id}'",
    )


@router.post("/articles/{article_id}/requeue-writing")
def requeue_writing_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Relance la rédaction d'un article en échec ou bloqué (remise en file d'attente)."""
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status_reason_id not in (ArticleStatus.FAILED, ArticleStatus.WRITING_IN_PROGRESS, ArticleStatus.WRITING_REQUESTED):
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de relancer la rédaction depuis le statut '{article.status_reason_id}'",
        )
    title = article.current_revision.title if article.current_revision else ""
    set_article_status(article, ArticleStatus.WRITING_REQUESTED)
    article.updated_at = datetime.now(timezone.utc)
    log_step(
        db, article.project_id,
        f"Rédaction relancée manuellement : {title}",
        level="info", step="writing_queue", article_id=article.id,
    )
    db.commit()
    db.refresh(article)
    return {
        "id": article.id,
        "title": title,
        "status": article.status_reason_id,
    }


@router.get("/projects/{project_id}/production/queue")
def get_production_queue_route(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin", "editor")),
):
    return get_queue_summary(db, project_id)


@router.post("/projects/{project_id}/production/process")
def process_production_queue_route(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin")),
):
    from app.services.production_queue import process_writing_queue
    outcome = process_writing_queue(db, project_id)
    ids = [r["id"] for r in outcome["results"] if r.get("status") != "not_found"]
    articles = db.execute(select(Article).where(Article.id.in_(ids))).scalars().all() if ids else []
    return {
        "processed": len(articles),
        "requeued_stale": outcome["requeued_stale"],
        "articles": [{"id": a.id, "title": a.current_revision.title if a.current_revision else "", "status": a.status_reason_id} for a in articles],
    }


@router.delete("/projects/{project_id}/ideas/{article_id}", status_code=204)
def delete_idea_route(
    project_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    if article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Idea not found in project")
    _check_role(db, current_user.id, project_id, ("owner", "admin", "editor"))
    refusal = _idea_delete_refusal(article)
    if refusal:
        raise HTTPException(status_code=400, detail=refusal)
    db.delete(article)
    db.commit()


@router.post("/projects/{project_id}/ideas/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_ideas_route(
    project_id: str,
    body: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_role(db, current_user.id, project_id, ("owner", "admin", "editor"))
    requested_ids = list(dict.fromkeys(body.article_ids))
    if not requested_ids:
        raise HTTPException(status_code=400, detail="Aucune idée sélectionnée.")

    articles = db.execute(
        select(Article).where(Article.id.in_(requested_ids), Article.project_id == project_id)
    ).scalars().all()
    by_id = {article.id: article for article in articles}
    deleted_ids: list[str] = []
    skipped_items: list[dict[str, str]] = []

    for idea_id in requested_ids:
        article = by_id.get(idea_id)
        if not article:
            skipped_items.append({"id": idea_id, "reason": "Idée introuvable dans ce projet."})
            continue
        refusal = _idea_delete_refusal(article)
        if refusal:
            skipped_items.append({"id": idea_id, "reason": refusal})
            continue
        db.delete(article)
        deleted_ids.append(idea_id)

    if not deleted_ids:
        detail = skipped_items[0]["reason"] if skipped_items else "Aucune idée supprimable."
        raise HTTPException(status_code=400, detail=detail)

    db.commit()
    deleted_count = len(deleted_ids)
    skipped_count = len(skipped_items)
    message = (
        f"{deleted_count} supprimée(s), {skipped_count} ignorée(s)."
        if skipped_count
        else f"{deleted_count} idée(s) supprimée(s)."
    )
    return {
        "deleted": deleted_count,
        "skipped": skipped_count,
        "deleted_ids": deleted_ids,
        "skipped_items": skipped_items,
        "message": message,
    }


@router.post("/articles/{article_id}/restore-idea")
def restore_idea_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))
    if article.status_reason_id != ArticleStatus.IDEA_REJECTED:
        raise HTTPException(status_code=400, detail="Only rejected ideas can be restored")
    title = article.current_revision.title if article.current_revision else ""
    set_article_status(article, ArticleStatus.IDEA_PROPOSED)
    article.rejection_reason = None
    article.rejection_note = None
    article.updated_at = datetime.now(timezone.utc)
    log_step(db, article.project_id, f"Idée restaurée : {title}", level="info", step="restore", article_id=article.id)
    db.commit()
    return {"status": "restored", "id": article.id, "title": title}
