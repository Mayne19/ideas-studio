import json
from math import ceil

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.project import Project
from app.models.pipeline import ProjectPipeline
from app.services.scheduler import generate_daily_ideas
from app.services.optimization_engine import review_published_articles
from app.services.notification_service import create_notification
from app.services.log_service import log_step


def run_daily_project_tasks(db: Session, project_id: str) -> dict:
    ideas_result = _run_ideas(db, project_id)
    review_result = review_published_articles(db, project_id)

    generated_count = ideas_result.get("generated", 0)

    articles_created = 0
    if generated_count > 0:
        create_notification(
            db,
            project_id=project_id,
            title="Nouvelles idées générées",
            message=f"{generated_count} idée(s) générée(s) aujourd'hui.",
            level="success",
            type="daily_ideas",
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
    projects = db.execute(select(Project).where(Project.status != "archived")).scalars().all()

    results = []
    for project in projects:
        result = run_daily_project_tasks(db, project.id)
        results.append(result)

    return {
        "projects_processed": len(projects),
        "results": results,
    }


def _run_ideas(db: Session, project_id: str) -> dict:
    from app.services.idea_engine import generate_idea
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.core.config import settings
    from app.models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"generated": 0, "skipped": 0}
    pipeline = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()

    llm = get_llm_provider()
    search = get_search_provider()

    active_days = []
    if pipeline and pipeline.active_days:
        try:
            active_days = json.loads(pipeline.active_days)
        except Exception:
            active_days = []
    active_day_count = len(active_days) or 7
    weekly_target = max(1, pipeline.articles_per_week) if pipeline else settings.IDEAS_PER_DAY
    daily_target = max(1, ceil(weekly_target / active_day_count))

    generated = 0
    skipped = 0
    if pipeline and pipeline.category_priorities and pipeline.category_priorities != "{}":
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
            project_audience=project.audience,
            project_language=project.language,
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
