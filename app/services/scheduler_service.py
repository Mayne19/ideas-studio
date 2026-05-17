from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.project import Project
from app.services.scheduler import generate_daily_ideas
from app.services.optimization_engine import review_published_articles
from app.services.notification_service import create_notification


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

    llm = get_llm_provider()
    search = get_search_provider()

    generated = 0
    skipped = 0
    for _ in range(settings.IDEAS_PER_DAY):
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

    return {"generated": generated, "skipped": skipped}
