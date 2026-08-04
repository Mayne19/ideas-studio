"""Background worker that runs scheduled tasks using APScheduler."""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.core.database import SessionLocal, set_current_project_id
from app.models.ai import Pipeline
from app.models.core import Project
from app.services.scheduler_service import is_generation_due, generation_already_ran
from app.services.pipeline_service import run_pipeline

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)


def check_scheduled_publications():
    """Publish articles whose scheduled_for time has passed."""
    from app.models.content import Article
    from app.models.reference import ArticleStatus
    from app.services.article_lifecycle_service import publish_article

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # content.articles est sous RLS (project_id) : on parcourt les projets
        # un par un et on pose le contexte avant chaque lot, une requête
        # globale cross-projet reverrait toujours 0 ligne.
        project_ids = db.execute(select(Project.id)).scalars().all()
        for project_id in project_ids:
            set_current_project_id(project_id)
            articles = db.execute(
                select(Article).where(
                    Article.project_id == project_id,
                    Article.scheduled_for.isnot(None),
                    Article.scheduled_for <= now,
                    Article.status_reason_id == ArticleStatus.SCHEDULED,
                )
            ).scalars().all()
            for article in articles:
                try:
                    publish_article(db, article)
                    logger.info("Scheduled publication: article %s published", article.id)
                except Exception as e:
                    logger.error("Failed to publish scheduled article %s: %s", article.id, e)
        db.commit()
    finally:
        set_current_project_id(None)
        db.close()


def check_scheduled_idea_generation():
    """Déclenche la génération d'idées uniquement pour les projets dont
    l'échéance configurée (ideas_frequency + launch_day + launch_hour, voir
    app.services.scheduler_service.is_generation_due) correspond exactement à
    maintenant. Aucune génération en dehors de cette échéance précise."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pipelines = db.execute(
            select(Pipeline).where(Pipeline.is_enabled.is_(True))
        ).scalars().all()
        for pipeline in pipelines:
            # run_pipeline committe et expire la session : recharger avant tout accès aux attributs
            db.refresh(pipeline)
            set_current_project_id(pipeline.project_id)
            schedule = pipeline.schedule or {}
            if not is_generation_due(schedule, now):
                continue
            if generation_already_ran(db, pipeline.project_id, schedule, now):
                continue
            try:
                result = run_pipeline(db, pipeline.project_id)
                logger.info(
                    "Scheduled pipeline run for project %s: %s ideas, %s articles",
                    pipeline.project_id,
                    result.get("ideas_generated", 0),
                    result.get("articles_created", 0),
                )
            except Exception as e:
                logger.error("Scheduled pipeline failed for project %s: %s", pipeline.project_id, e)
    finally:
        set_current_project_id(None)
        db.close()


def process_writing_queues():
    """Drain the article writing queues for all projects with pending work."""
    from app.models.content import Article
    from app.models.reference import ArticleStatus
    from app.services.production_queue import process_writing_queue

    db = SessionLocal()
    try:
        # content.articles est sous RLS : impossible de repérer les projets
        # avec du travail en attente par une requête cross-projet, on pose le
        # contexte projet par projet avant de vérifier chacun.
        project_ids = db.execute(select(Project.id)).scalars().all()
        for project_id in project_ids:
            set_current_project_id(project_id)
            has_pending = db.execute(
                select(Article.id)
                .where(
                    Article.project_id == project_id,
                    Article.status_reason_id.in_((ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS)),
                )
                .limit(1)
            ).scalar_one_or_none()
            if not has_pending:
                continue
            try:
                outcome = process_writing_queue(db, project_id)
                if outcome["claimed"] or outcome["requeued_stale"]:
                    logger.info(
                        "Writing queue project=%s claimed=%s requeued_stale=%s",
                        project_id, outcome["claimed"], outcome["requeued_stale"],
                    )
            except Exception as e:
                logger.error("Writing queue failed for project %s: %s", project_id, e)
    finally:
        set_current_project_id(None)
        db.close()


def start_scheduler():
    """Start the background scheduler with all recurring jobs."""
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    scheduler.add_job(
        check_scheduled_publications,
        trigger=CronTrigger(minute="*/5"),
        id="check_scheduled_publications",
        replace_existing=True,
    )

    scheduler.add_job(
        check_scheduled_idea_generation,
        trigger=CronTrigger(minute="0"),
        id="check_scheduled_idea_generation",
        replace_existing=True,
    )

    scheduler.add_job(
        process_writing_queues,
        trigger=CronTrigger(minute="*/2"),
        id="process_writing_queues",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Background scheduler started with jobs: check_scheduled_publications, check_scheduled_idea_generation, process_writing_queues")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
