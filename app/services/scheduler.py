from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.project import Project
from app.services.idea_engine import generate_idea
from app.services.providers.llm_provider import get_llm_provider
from app.services.providers.search_provider import get_search_provider
from app.services.log_service import log_step
from app.core.config import settings


def generate_daily_ideas(db: Session) -> dict:
    """Generate ideas for all active projects, up to IDEAS_PER_DAY per project."""
    llm = get_llm_provider()
    search = get_search_provider()

    projects = db.execute(select(Project).where(Project.status != "archived")).scalars().all()

    total_generated = 0
    total_skipped = 0

    for project in projects:
        project_generated = 0
        for _ in range(settings.IDEAS_PER_DAY):
            idea = generate_idea(
                db=db,
                project_id=project.id,
                project_audience=project.audience,
                project_language=project.language,
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
