import json
from math import ceil
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from app.models.pipeline import ProjectPipeline
from app.models.pipeline_log import PipelineLog
from app.models.article import Article
from app.models.category import Category
from app.schemas.pipeline import PipelineSettingsUpdate, PipelineSettingsPublic, PipelineLogPublic

logger = logging.getLogger(__name__)


def _parse_json_field(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _category_frequency_summary(db: Session, project_id: str) -> tuple[int, list[dict]]:
    categories = (
        db.query(Category)
        .filter(Category.project_id == project_id)
        .order_by(Category.priority.desc(), Category.name.asc())
        .all()
    )
    rows = []
    total = 0
    for category in categories:
        enabled = category.pipeline_enabled is not False
        frequency = category.monthly_frequency if category.monthly_frequency is not None else category.target_frequency
        if enabled and frequency:
            total += max(0, int(frequency))
        rows.append({
            "id": category.id,
            "name": category.name,
            "monthly_frequency": frequency,
            "pipeline_enabled": enabled,
            "priority": category.priority,
        })
    return total, rows


def _model_to_settings(pipe: ProjectPipeline, db: Session | None = None) -> PipelineSettingsPublic:
    launch_hours = _parse_json_field(pipe.launch_hours, None) if pipe.launch_hours else None
    if isinstance(launch_hours, list) and all(isinstance(h, str) for h in launch_hours):
        pass
    else:
        launch_hours = None

    total_monthly = None
    categories_frequencies = []
    if db is not None:
        total_monthly, categories_frequencies = _category_frequency_summary(db, pipe.project_id)

    return PipelineSettingsPublic(
        id=pipe.id,
        project_id=pipe.project_id,
        enabled=pipe.enabled,
        active_days=_parse_json_field(pipe.active_days, []),
        launch_hour=pipe.launch_hour,
        articles_per_week=pipe.articles_per_week,
        category_priorities=_parse_json_field(pipe.category_priorities, {}),
        ideas_per_week=pipe.ideas_per_week,
        max_pending_drafts=pipe.max_pending_drafts,
        paused_until=pipe.paused_until,
        paused_indefinitely=pipe.paused_indefinitely,
        default_quality_mode=pipe.default_quality_mode,
        launch_hours=launch_hours,
        cost_limit_per_article_eur=pipe.cost_limit_per_article_eur,
        total_monthly_from_categories=total_monthly,
        categories_frequencies=categories_frequencies,
        automation_notes="Worker automatique APScheduler disponible seulement si le processus worker est lance. Le lancement manuel reste disponible.",
        created_at=pipe.created_at,
        updated_at=pipe.updated_at,
    )


def get_or_create_pipeline(db: Session, project_id: str) -> ProjectPipeline:
    pipe = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()
    if pipe:
        return pipe
    pipe = ProjectPipeline(project_id=project_id)
    db.add(pipe)
    db.commit()
    db.refresh(pipe)
    return pipe


def get_pipeline(db: Session, project_id: str) -> PipelineSettingsPublic | None:
    pipe = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()
    if not pipe:
        return PipelineSettingsPublic(
            id="",
            project_id=project_id,
            enabled=False,
            active_days=[],
            launch_hour=8,
            articles_per_week=5,
            category_priorities={},
            ideas_per_week=5,
            max_pending_drafts=10,
            paused_until=None,
            paused_indefinitely=False,
            default_quality_mode="quality",
            launch_hours=None,
            cost_limit_per_article_eur=None,
            total_monthly_from_categories=_category_frequency_summary(db, project_id)[0],
            categories_frequencies=_category_frequency_summary(db, project_id)[1],
            automation_notes="Pipeline non créé. Configurez-le avant automatisation ; lancement manuel disponible après création.",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    return _model_to_settings(pipe, db=db)


def update_pipeline(db: Session, project_id: str, data: PipelineSettingsUpdate) -> PipelineSettingsPublic:
    pipe = get_or_create_pipeline(db, project_id)
    update_dict = data.model_dump(exclude_unset=True)
    if "active_days" in update_dict:
        update_dict["active_days"] = json.dumps(update_dict["active_days"])
    if "category_priorities" in update_dict:
        update_dict["category_priorities"] = json.dumps(update_dict["category_priorities"])
    if "launch_hours" in update_dict:
        update_dict["launch_hours"] = json.dumps(update_dict["launch_hours"]) if update_dict["launch_hours"] else None
    for field, value in update_dict.items():
        if field == "launch_hours" and value is not None:
            setattr(pipe, field, json.dumps(value))
        else:
            setattr(pipe, field, value)
    pipe.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pipe)
    return _model_to_settings(pipe, db=db)


def _count_pending_drafts(db: Session, project_id: str) -> int:
    return db.query(Article).filter(
        Article.project_id == project_id,
        Article.status.in_(["draft", "draft_ready", "writing_in_progress"]),
    ).count()


def _is_paused(pipe: ProjectPipeline) -> bool:
    if pipe.paused_indefinitely:
        return True
    if pipe.paused_until and pipe.paused_until > datetime.now(timezone.utc):
        return True
    return False


def run_pipeline(db: Session, project_id: str) -> dict:
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.services.idea_engine import generate_idea
    from app.services.agents.agent_router import get_agent_router
    from app.models.project import Project

    pipe = get_or_create_pipeline(db, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()

    log_entry = PipelineLog(
        project_id=project_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(log_entry)
    db.flush()

    errors = []
    ideas_generated = 0
    articles_created = 0
    pipeline_mode = settings.PIPELINE_MODE

    try:
        if _is_paused(pipe):
            errors.append("Pipeline is paused")
            log_entry.status = "skipped"
        else:
            max_drafts = pipe.max_pending_drafts or 10
            pending = _count_pending_drafts(db, project_id)
            if pending >= max_drafts:
                errors.append(f"Max pending drafts reached ({pending}/{max_drafts})")
                log_entry.status = "skipped"
            else:
                llm = get_llm_provider()
                search = get_search_provider()
                agent_router = get_agent_router(db=db)

                active_days = []
                if pipe.active_days:
                    try:
                        active_days = json.loads(pipe.active_days) if isinstance(pipe.active_days, str) else pipe.active_days
                    except Exception:
                        active_days = []
                active_day_count = len(active_days) or 7
                weekly_target = max(1, pipe.articles_per_week or 5)
                daily_target = max(1, ceil(weekly_target / active_day_count))
                project_audience = project.audience if project else None
                project_language = project.language if project else "fr"

                # Phase 1: Generate ideas (always)
                for i in range(daily_target):
                    try:
                        idea = generate_idea(
                            db=db,
                            project_id=project_id,
                            project_audience=project_audience,
                            project_language=project_language,
                            llm=llm,
                            search=search,
                            agent_router=agent_router,
                        )
                        if idea:
                            ideas_generated += 1
                    except Exception as exc:
                        logger.exception("Pipeline idea generation failed")
                        errors.append(f"Idea {i + 1}: {exc}")

                # Phase 2: Generate briefs / full drafts based on pipeline mode
                if pipeline_mode in ("brief_only", "draft_generation") and ideas_generated > 0:
                    from app.services.seo.seo_generation_orchestrator import generate_full_article

                    pending_ideas = (
                        db.query(Article)
                        .filter(
                            Article.project_id == project_id,
                            Article.status == "idea_proposed",
                        )
                        .order_by(Article.opportunity_score.desc().nullslast())
                        .limit(daily_target)
                        .all()
                    )
                    for idea in pending_ideas:
                        try:
                            article = generate_full_article(
                                db=db,
                                project_id=project_id,
                                llm=llm,
                                search=search,
                                preferred_title=idea.title,
                                keyword=idea.keyword,
                                category_id=idea.category_id,
                                audience=idea.audience,
                                angle=idea.angle,
                                search_intent=idea.search_intent,
                                agent_router=agent_router,
                            )
                            if pipeline_mode == "brief_only":
                                article.status = "draft"
                            else:
                                article.status = "draft_ready"
                            articles_created += 1
                        except Exception as exc:
                            logger.exception("Pipeline article generation failed")
                            errors.append(f"Article from idea {idea.id}: {exc}")

                log_entry.status = "completed" if not errors else "completed_with_errors"
    except Exception as exc:
        logger.exception("Pipeline run failed for project %s", project_id)
        errors.append(str(exc))
        log_entry.status = "failed"

    log_entry.ideas_generated = ideas_generated
    log_entry.articles_created = articles_created
    log_entry.errors = "\n".join(errors) if errors else None
    log_entry.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log_entry)

    return {
        "status": log_entry.status,
        "ideas_generated": ideas_generated,
        "articles_created": articles_created,
        "pipeline_mode": pipeline_mode,
    }


def list_pipeline_logs(db: Session, project_id: str, limit: int = 20) -> list[PipelineLogPublic]:
    logs = (
        db.query(PipelineLog)
        .filter(PipelineLog.project_id == project_id)
        .order_by(PipelineLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        PipelineLogPublic(
            id=log.id,
            project_id=log.project_id,
            status=log.status,
            ideas_generated=log.ideas_generated,
            articles_created=log.articles_created,
            errors=log.errors,
            started_at=log.started_at,
            finished_at=log.finished_at,
        )
        for log in logs
    ]
