from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.core import Project
from app.models.ai import Pipeline, PipelineRun
from app.models.reference import ProjectStatus, RunStatus
from app.services.optimization_engine import review_published_articles
from app.services.notification_service import create_notification
from app.services.log_service import log_step
from app.services.idea_engine import generate_idea
from app.services.providers.llm_provider import get_llm_provider
from app.services.providers.search_provider import get_search_provider
from app.core.config import settings


def is_generation_due(schedule: dict, now: datetime) -> bool:
    """Le déclenchement de la génération d'idées est strictement piloté par la
    configuration utilisateur (ideas_frequency + launch_day + launch_hour) —
    aucune génération ne doit avoir lieu en dehors de cette échéance précise.
    Voir PipelineSettingsUpdate.ideas_frequency pour la sémantique de launch_day."""
    frequency = schedule.get("ideas_frequency") or ("monthly" if schedule.get("ideas_day_of_month") else None)
    launch_hour = schedule.get("launch_hour")
    if frequency is None or launch_hour is None or launch_hour != now.hour:
        return False

    if frequency == "daily":
        return True

    launch_day = schedule.get("launch_day", schedule.get("ideas_day_of_month"))
    if launch_day is None:
        return False

    if frequency == "weekly":
        return now.weekday() == launch_day
    if frequency == "monthly":
        return now.day == launch_day
    if frequency == "quarterly":
        return now.day == launch_day and now.month in (1, 4, 7, 10)
    return False


def _generation_window_start(schedule: dict, now: datetime) -> datetime:
    """Début de la fenêtre d'échéance courante, pour l'anti-double-exécution :
    une seule génération par échéance, même si le job cron tourne plusieurs
    fois pendant l'heure ou si le process redémarre."""
    frequency = schedule.get("ideas_frequency") or "monthly"
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == "daily":
        return today_start
    return today_start - timedelta(hours=1)  # weekly/monthly/quarterly : une occurrence par jour suffit


def generation_already_ran(db: Session, project_id: str, schedule: dict, now: datetime) -> bool:
    window_start = _generation_window_start(schedule, now)
    return db.execute(
        select(PipelineRun.id).where(
            PipelineRun.project_id == project_id,
            PipelineRun.started_at >= window_start,
            PipelineRun.status_reason_id.in_((RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.SUCCEEDED)),
        ).limit(1)
    ).scalar_one_or_none() is not None


def generate_daily_ideas(db: Session) -> dict:
    """Generate ideas for all active projects, up to IDEAS_PER_DAY per project."""
    llm = get_llm_provider()
    search = get_search_provider()

    projects = db.execute(select(Project).where(Project.status_reason_id != ProjectStatus.ARCHIVED)).scalars().all()

    total_generated = 0
    total_skipped = 0

    for project in projects:
        profile = project.active_editorial_profile
        project_generated = 0
        for _ in range(settings.IDEAS_PER_DAY):
            idea = generate_idea(
                db=db,
                project_id=project.id,
                project_audience=profile.audience if profile else None,
                project_language=project.locale.split("-")[0] if project.locale else "fr",
                llm=llm,
                search=search,
            )
            if idea is not None:
                project_generated += 1
                total_generated += 1
            else:
                total_skipped += 1

        if project_generated > 0:
            log_step(
                db,
                project.id,
                f"Scheduler : {project_generated} idée(s) générée(s) pour le projet",
                level="info",
                step="daily_scheduler",
            )

    db.commit()
    return {"generated": total_generated, "skipped": total_skipped, "projects": len(projects)}


def run_daily_project_tasks(db: Session, project_id: str) -> dict:
    ideas_result = _run_ideas(db, project_id)
    review_result = review_published_articles(db, project_id)

    generated_count = ideas_result.get("generated", 0)

    articles_created = 0
    if generated_count > 0:
        create_notification(
            db,
            project_id=project_id,
            title=f"{generated_count} idées prêtes à valider",
            message=(
                f"Le pipeline a généré {generated_count} idée(s) ce mois-ci. "
                f"Validez-les avant la fin du mois pour lancer la production."
            ),
            level="success",
            type="monthly_ideas_ready",
            link=f"/projects/{project_id}/production?tab=ideas",
        )

    db.commit()
    return {
        "project_id": project_id,
        "ideas": ideas_result,
        "review": review_result,
        "ideas_generated": generated_count,
        "articles_created": articles_created,
    }


def run_all_projects_daily_tasks(db: Session) -> dict:
    projects = db.execute(select(Project).where(Project.status_reason_id != ProjectStatus.ARCHIVED)).scalars().all()

    results = []
    for project in projects:
        result = run_daily_project_tasks(db, project.id)
        results.append(result)

    return {
        "projects_processed": len(projects),
        "results": results,
    }


def _run_ideas(db: Session, project_id: str) -> dict:
    project = db.get(Project, project_id)
    if not project:
        return {"generated": 0, "skipped": 0}
    profile = project.active_editorial_profile
    pipeline = db.get(Pipeline, project_id)

    llm = get_llm_provider()
    search = get_search_provider()

    schedule = pipeline.schedule if pipeline else {}
    active_days = schedule.get("active_days", []) if schedule else []
    active_day_count = len(active_days) or 7
    weekly_target = max(1, pipeline.articles_per_week) if pipeline else settings.IDEAS_PER_DAY
    daily_target = max(1, ceil(weekly_target / active_day_count))

    generated = 0
    skipped = 0
    if schedule and schedule.get("category_priorities"):
        log_step(
            db,
            project_id,
            "Pipeline : category_priorities détecté mais non encore appliqué. Génération d'idées uniquement pour l'instant.",
            level="info",
            step="daily_scheduler",
        )
    for _ in range(daily_target):
        idea = generate_idea(
            db=db,
            project_id=project_id,
            project_audience=profile.audience if profile else None,
            project_language=project.locale.split("-")[0] if project.locale else "fr",
            llm=llm,
            search=search,
        )
        if idea:
            generated += 1
        else:
            skipped += 1

    log_step(
        db,
        project_id,
        f"Pipeline : {generated} idée(s) créée(s), {skipped} ignorée(s), cible quotidienne={daily_target}, mode=ideas_only.",
        level="info",
        step="daily_scheduler",
    )
    return {"generated": generated, "skipped": skipped, "daily_target": daily_target, "mode": "ideas_only"}
