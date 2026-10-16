"""Génération d'article en tâche de fond (ai.generation_jobs).

Le proxy HTTP de Railway coupe toute requête à 300 s ; la rédaction section
par section prend 7 à 12 min. POST /projects/{id}/articles/generate crée donc
un job et répond 202 tout de suite ; la génération tourne dans un pool de
threads borné (MAX_CONCURRENT_GENERATIONS), chacune avec sa propre session
SQLAlchemy, et le client suit le job par polling (GET .../generation-jobs/{id}).

Même modèle d'exécution que la file de rédaction (production_queue.py :
thread dédié, session propre, contexte projet reposé dans le thread). Le
process est unique (une réplique, un worker uvicorn) : le pool est en mémoire,
et au démarrage les jobs laissés queued/running par le process précédent sont
marqués en échec (fail_interrupted_jobs) — ils ne seront jamais repris.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.ai import GenerationJob
from app.models.reference import ArticleStatus, RunStatus, STATE_ID_BY_RUN_STATUS, set_run_status

logger = logging.getLogger(__name__)

MAX_CONCURRENT_GENERATIONS = 2
INTERRUPTED_ERROR = "Interrompu par un redémarrage du serveur."

STATUS_CODES: dict[int, str] = {
    RunStatus.QUEUED: "queued",
    RunStatus.RUNNING: "running",
    RunStatus.SUCCEEDED: "succeeded",
    RunStatus.FAILED: "failed",
    RunStatus.CANCELLED: "cancelled",
}

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=MAX_CONCURRENT_GENERATIONS, thread_name_prefix="article-generation",
            )
        return _executor


def shutdown_executor() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None


def job_to_dict(job: GenerationJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "project_id": job.project_id,
        "status": STATUS_CODES.get(job.status_reason_id, "queued"),
        "article_id": job.article_id,
        "current_step": job.current_step,
        "steps_completed": job.steps_completed or 0,
        "error": job.error,
        "title": (job.request or {}).get("preferred_title") or (job.request or {}).get("keyword"),
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def create_generation_job(db: Session, project_id: str, user_id: str | None, request: dict) -> GenerationJob:
    job = GenerationJob(project_id=project_id, user_id=user_id, request=request or {})
    set_run_status(job, RunStatus.QUEUED)
    db.add(job)
    db.flush()
    return job


def get_generation_job(db: Session, project_id: str, job_id: str) -> GenerationJob | None:
    job = db.get(GenerationJob, job_id)
    if job is None or job.project_id != project_id:
        return None
    return job


def list_generation_jobs(db: Session, project_id: str, limit: int = 10, active_only: bool = False) -> list[GenerationJob]:
    query = select(GenerationJob).where(GenerationJob.project_id == project_id)
    if active_only:
        query = query.where(GenerationJob.status_reason_id.in_((RunStatus.QUEUED, RunStatus.RUNNING)))
    query = query.order_by(GenerationJob.created_at.desc()).limit(max(1, min(limit, 50)))
    return list(db.execute(query).scalars().all())


def fail_interrupted_jobs(db: Session) -> int:
    """Au démarrage : un job queued/running ne peut appartenir qu'au process
    précédent (pool en mémoire, réplique unique) — il ne finira jamais."""
    result = db.execute(
        update(GenerationJob)
        .where(GenerationJob.status_reason_id.in_((RunStatus.QUEUED, RunStatus.RUNNING)))
        .values(
            status_reason_id=RunStatus.FAILED,
            state_id=STATE_ID_BY_RUN_STATUS[RunStatus.FAILED],
            error=INTERRUPTED_ERROR,
            finished_at=_now(),
            updated_at=_now(),
        )
    )
    db.commit()
    return result.rowcount or 0


def _update_job(job_id: str, **values: Any) -> None:
    """Écrit l'état du job dans une session courte et indépendante : la
    session de génération garde sa transaction ouverte jusqu'à la fin de
    l'article, la progression doit être visible avant."""
    from app.core.database import SessionLocal

    status = values.pop("status", None)
    if status is not None:
        values["status_reason_id"] = status
        values["state_id"] = STATE_ID_BY_RUN_STATUS[status]
    values["updated_at"] = _now()
    db = SessionLocal()
    try:
        db.execute(update(GenerationJob).where(GenerationJob.id == job_id).values(**values))
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("generation_job: mise à jour du job %s impossible", job_id, exc_info=True)
    finally:
        db.close()


def submit_generation_job(job_id: str, project_id: str) -> None:
    _get_executor().submit(run_generation_job, job_id, project_id)


def _failure_message(exc: Exception) -> str:
    from app.services.providers.llm_provider import GenerationFailedError, ProviderUnavailableError

    if isinstance(exc, ProviderUnavailableError):
        return f"Provider IA indisponible : {exc}"
    if isinstance(exc, GenerationFailedError):
        return f"La génération a échoué : {exc}"
    return f"Erreur inattendue pendant la génération : {exc}"


def run_generation_job(job_id: str, project_id: str) -> None:
    """Exécute un job (dans un thread du pool) ; ne lève jamais."""
    from app.core.database import SessionLocal, set_current_project_id
    from app.models.content import Article
    from app.models.core import Project
    from app.services.agents.agent_router import get_agent_router
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.services.seo.seo_generation_orchestrator import generate_full_article

    set_current_project_id(project_id)
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        request = dict(job.request or {})
        db.rollback()
        _update_job(job_id, status=RunStatus.RUNNING, started_at=_now(), current_step="Préparation")

        def on_progress(step: str, count: int) -> None:
            _update_job(job_id, current_step=step[:200], steps_completed=min(count, 32000))

        try:
            project = db.get(Project, project_id)
            if project is None:
                raise RuntimeError("Projet introuvable.")
            profile = project.active_editorial_profile
            llm = get_llm_provider(project_id=project_id)
            search = get_search_provider(project_id)
            logger.info(
                "generation_job_start job=%s provider=%s model=%s project=%s",
                job_id, llm.provider_name, llm.model_name, project_id,
            )
            article = generate_full_article(
                db=db,
                project_id=project_id,
                llm=llm,
                search=search,
                agent_router=get_agent_router(db=db),
                preferred_title=request.get("preferred_title"),
                keyword=request.get("keyword"),
                category_id=request.get("category_id"),
                audience=request.get("audience") or (profile.audience if profile else None),
                angle=request.get("angle"),
                search_intent=request.get("search_intent"),
                context_hint=request.get("context_hint"),
                expert_notes=request.get("expert_notes"),
                include_faq=request.get("include_faq"),
                include_callouts=request.get("include_callouts"),
                progress_cb=on_progress,
            )
            db.commit()
            article = db.get(Article, article.id)
        except Exception as exc:
            logger.exception("generation_job_failed job=%s project=%s", job_id, project_id)
            db.rollback()
            _update_job(job_id, status=RunStatus.FAILED, error=_failure_message(exc)[:2000], finished_at=_now())
            return

        if article is not None and article.status_reason_id == ArticleStatus.FAILED:
            _update_job(
                job_id, status=RunStatus.FAILED, article_id=article.id, finished_at=_now(),
                error="La rédaction a échoué : consultez le rapport de génération de l'article.",
            )
            return
        _update_job(
            job_id, status=RunStatus.SUCCEEDED, article_id=article.id if article else None,
            current_step="Terminé", finished_at=_now(),
        )
        logger.info("generation_job_done job=%s article=%s", job_id, article.id if article else None)
    except Exception:
        logger.exception("generation_job: erreur inattendue job=%s", job_id)
        _update_job(job_id, status=RunStatus.FAILED, error="Erreur interne du job de génération.", finished_at=_now())
    finally:
        db.close()
        set_current_project_id(None)
