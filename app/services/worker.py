"""Background worker that runs scheduled tasks using APScheduler."""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.database import SessionLocal
from app.models.project import Project
from app.models.pipeline import ProjectPipeline
from app.services.scheduler_service import run_daily_project_tasks
from app.services.pipeline_service import run_pipeline

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)


def check_scheduled_publications():
    """Publish articles whose scheduled_at time has passed."""
    from app.models.article import Article
    from app.services.article_service import publish_article

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        articles = (
            db.query(Article)
            .filter(
                Article.scheduled_at.isnot(None),
                Article.scheduled_at <= now,
                Article.status == "scheduled",
            )
            .all()
        )
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
        projects = db.query(Project).all()
        for project in projects:
            try:
                run_daily_project_tasks(db, project.id)
                logger.info("Daily tasks completed for project %s", project.id)
            except Exception as e:
                logger.error("Daily tasks failed for project %s: %s", project.id, e)
    finally:
        db.close()


def run_pipelines():
    """Run automated pipelines for projects with pipeline enabled."""
    db = SessionLocal()
    try:
        pipelines = db.query(ProjectPipeline).filter(ProjectPipeline.enabled == True).all()
        for pipeline in pipelines:
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

    scheduler.start()
    logger.info("Background scheduler started with jobs: check_scheduled_publications, run_daily_tasks, run_pipelines")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
