import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.content import Article
from app.models.ai import Pipeline, WorkflowRun
from app.models.reference import ArticleStatus, RunStatus, WorkflowPhase, set_article_status, set_run_status
from app.services.log_service import log_step

logger = logging.getLogger(__name__)

WRITING_STALE_MINUTES = 30
# Au-delà de ce nombre de reprises automatiques sur les dernières 24h, on
# arrête d'insister : l'échec est probablement réel (pas un simple crash
# serveur/déploiement), l'article repasse en FAILED pour relance manuelle.
MAX_AUTO_REQUEUE_ATTEMPTS = 3


def _latest_run(db: Session, article_id: str) -> WorkflowRun | None:
    return db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.article_id == article_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def send_to_production(db: Session, article_id: str) -> Article | None:
    """Move an idea into the production queue — le suivi agent par agent est
    porté par ai.workflow_runs/workflow_steps, plus par des colonnes article."""
    article = db.get(Article, article_id)
    if not article:
        return None
    if article.status_reason_id not in (ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY):
        logger.warning("Article %s has status %s, cannot send to production", article_id, article.status_reason_id)
        return None

    set_article_status(article, ArticleStatus.WRITING_REQUESTED)
    article.updated_at = datetime.now(timezone.utc)

    run = WorkflowRun(article_id=article.id, phase_id=WorkflowPhase.PLANNING)
    set_run_status(run, RunStatus.QUEUED)
    db.add(run)

    title = article.current_revision.title if article.current_revision else ""
    log_step(
        db, article.project_id,
        f"Idée envoyée en production : {title}",
        level="info", step="send_to_production", article_id=article.id,
    )
    db.flush()
    return article


def _recent_requeue_attempts(db: Session, article_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return len(db.execute(
        select(WorkflowRun.id).where(
            WorkflowRun.article_id == article_id,
            WorkflowRun.started_at >= since,
        )
    ).scalars().all())


def requeue_stale_writing(db: Session, project_id: str, minutes: int = WRITING_STALE_MINUTES) -> int:
    """Remet en file les rédactions bloquées (writing_in_progress sans update depuis X minutes).
    Après MAX_AUTO_REQUEUE_ATTEMPTS tentatives sur 24h, bascule en FAILED
    plutôt que de reprendre indéfiniment un article qui échoue réellement."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stale = db.execute(
        select(Article).where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.WRITING_IN_PROGRESS,
            Article.updated_at < threshold,
        )
    ).scalars().all()
    for article in stale:
        title = article.current_revision.title if article.current_revision else ""
        if _recent_requeue_attempts(db, article.id) >= MAX_AUTO_REQUEUE_ATTEMPTS:
            set_article_status(article, ArticleStatus.FAILED)
            article.updated_at = datetime.now(timezone.utc)
            log_step(
                db, project_id,
                f"Rédaction bloquée après {MAX_AUTO_REQUEUE_ATTEMPTS} tentatives automatiques, marquée en échec : {title}",
                level="error", step="writing_queue", article_id=article.id,
            )
            continue
        set_article_status(article, ArticleStatus.WRITING_REQUESTED)
        article.updated_at = datetime.now(timezone.utc)
        log_step(
            db, project_id,
            f"Rédaction bloquée depuis plus de {minutes} min, remise en file : {title}",
            level="warning", step="writing_queue", article_id=article.id,
        )
    if stale:
        db.commit()
    return len(stale)


def claim_for_writing(db: Session, project_id: str, limit: int) -> list[str]:
    """Réclame atomiquement jusqu'à `limit` idées en file (writing_requested -> writing_in_progress).

    Le claim par UPDATE conditionnel garantit qu'aucun article n'est pris
    par deux workers en même temps.
    """
    candidate_ids = db.execute(
        select(Article.id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.WRITING_REQUESTED,
        )
        .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
        .limit(limit)
    ).scalars().all()

    claimed: list[str] = []
    for article_id in candidate_ids:
        updated = db.execute(
            Article.__table__.update()
            .where(
                Article.id == article_id,
                Article.status_reason_id == ArticleStatus.WRITING_REQUESTED,
            )
            .values(
                status_reason_id=ArticleStatus.WRITING_IN_PROGRESS,
                updated_at=datetime.now(timezone.utc),
            )
        ).rowcount
        if updated:
            claimed.append(article_id)
    db.commit()
    return claimed


def resolve_max_parallel(db: Session, project_id: str) -> int:
    pipe = db.get(Pipeline, project_id)
    value = pipe.max_parallel_jobs if pipe and pipe.max_parallel_jobs else 3
    return max(1, min(int(value), 10))


def process_writing_queue(db: Session, project_id: str, max_parallel: int | None = None) -> dict:
    """Expose la file au rédacteur local sans appeler l'ancien orchestrateur.

    Les sujets restent en ``WRITING_REQUESTED`` jusqu'au dépôt Markdown par le
    rédacteur. Les anciennes fonctions de claim sont conservées pour la
    compatibilité des appels de suivi, mais ne déclenchent plus de rédaction.
    """
    pending_ids = db.execute(
        select(Article.id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.WRITING_REQUESTED,
        )
        .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
    ).scalars().all()
    return {
        "requeued_stale": 0,
        "claimed": 0,
        "pending_local_writer": len(pending_ids),
        "results": [],
    }


def process_queue(db: Session, project_id: str, max_articles: int = 1) -> list[Article]:
    """Compat : draine la file via le nouveau mécanisme et retourne les articles traités."""
    outcome = process_writing_queue(db, project_id, max_parallel=max_articles)
    ids = [r["id"] for r in outcome["results"] if r.get("status") != "not_found"]
    if not ids:
        return []
    return db.execute(select(Article).where(Article.id.in_(ids))).scalars().all()


def get_queue_summary(db: Session, project_id: str) -> dict:
    """Get a summary of the production queue."""
    queue_statuses = [
        ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS,
        ArticleStatus.DRAFT_READY, ArticleStatus.REVIEW_NEEDED, ArticleStatus.CORRECTION_NEEDED,
    ]
    counts = {}
    total = 0
    for status in queue_statuses:
        cnt = db.execute(
            select(Article.id).where(
                Article.project_id == project_id,
                Article.status_reason_id == status,
            )
        ).scalars().all()
        counts[int(status)] = len(cnt)
        total += len(cnt)

    counts[int(ArticleStatus.FAILED)] = len(db.execute(
        select(Article.id).where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.FAILED,
        )
    ).scalars().all())

    next_up = db.execute(
        select(Article)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id.in_([ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS]),
        )
        .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
        .limit(1)
    ).scalars().first()

    return {
        "total_in_queue": total,
        "counts": counts,
        "next_up": {
            "id": next_up.id,
            "title": next_up.current_revision.title if next_up.current_revision else "",
        } if next_up else None,
    }
