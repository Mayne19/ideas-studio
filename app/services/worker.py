"""Background worker that runs scheduled tasks using APScheduler."""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.core import Project
from app.models.ai import Pipeline, PipelineRun
from app.models.reference import RunStatus
from app.services.scheduler_service import run_daily_project_tasks
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
        articles = db.execute(
            select(Article).where(
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
        db.close()


def run_daily_tasks():
    """Run daily tasks for all active projects."""
    db = SessionLocal()
    try:
        projects = db.execute(select(Project)).scalars().all()
        for project in projects:
            try:
                run_daily_project_tasks(db, project.id)
                logger.info("Daily tasks completed for project %s", project.id)
            except Exception as e:
                logger.error("Daily tasks failed for project %s: %s", project.id, e)
    finally:
        db.close()


def _pipeline_already_ran_today(db, project_id: str) -> bool:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.execute(
        select(PipelineRun.id).where(
            PipelineRun.project_id == project_id,
            PipelineRun.started_at >= today_start,
            PipelineRun.status_reason_id.in_((RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.SUCCEEDED)),
        ).limit(1)
    ).scalar_one_or_none() is not None


def check_monthly_idea_generation():
    """Trigger idea generation for pipelines configured for a specific day of month."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pipelines = db.execute(
            select(Pipeline).where(Pipeline.is_enabled.is_(True))
        ).scalars().all()
        for pipeline in pipelines:
            # run_pipeline committe et expire la session : recharger avant tout accès aux attributs
            db.refresh(pipeline)
            schedule = pipeline.schedule or {}
            ideas_day_of_month = schedule.get("ideas_day_of_month")
            launch_hour = schedule.get("launch_hour")
            if ideas_day_of_month is None or ideas_day_of_month != now.day:
                continue
            if launch_hour is None or launch_hour != now.hour:
                continue
            if _pipeline_already_ran_today(db, pipeline.project_id):
                continue
            try:
                result = run_pipeline(db, pipeline.project_id)
                logger.info(
                    "Monthly pipeline run for project %s: %s ideas, %s articles",
                    pipeline.project_id,
                    result.get("ideas_generated", 0),
                    result.get("articles_created", 0),
                )
            except Exception as e:
                logger.error("Monthly pipeline failed for project %s: %s", pipeline.project_id, e)
    finally:
        db.close()


def run_pipelines():
    """Run automated pipelines for projects with pipeline enabled."""
    db = SessionLocal()
    try:
        pipelines = db.execute(select(Pipeline).where(Pipeline.is_enabled.is_(True))).scalars().all()
        for pipeline in pipelines:
            # run_pipeline committe et expire la session : recharger avant tout accès aux attributs
            db.refresh(pipeline)
            if _pipeline_already_ran_today(db, pipeline.project_id):
                continue
            try:
                result = run_pipeline(db, pipeline.project_id)
                logger.info(
                    "Pipeline run for project %s: %s ideas, %s articles",
                    pipeline.project_id,
                    result.get("ideas_generated", 0),
                    result.get("articles_created", 0),
                )
            except Exception as e:
                logger.error("Pipeline failed for project %s: %s", pipeline.project_id, e)
    finally:
        db.close()


def process_writing_queues():
    """Drain the article writing queues for all projects with pending work."""
    from app.models.content import Article
    from app.models.reference import ArticleStatus
    from app.services.production_queue import process_writing_queue

    db = SessionLocal()
    try:
        project_ids = db.execute(
            select(Article.project_id)
            .where(Article.status_reason_id.in_((ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS)))
            .distinct()
        ).scalars().all()
        for project_id in project_ids:
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
        run_daily_tasks,
        trigger=CronTrigger(hour=6, minute=0),
        id="run_daily_tasks",
        replace_existing=True,
    )

    scheduler.add_job(
        run_pipelines,
        trigger=CronTrigger(minute="0"),
        id="run_pipelines",
        replace_existing=True,
    )

    scheduler.add_job(
        check_monthly_idea_generation,
        trigger=CronTrigger(minute="0"),
        id="check_monthly_idea_generation",
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
    logger.info("Background scheduler started with jobs: check_scheduled_publications, run_daily_tasks, run_pipelines, check_monthly_idea_generation, process_writing_queues")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
