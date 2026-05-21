import json
from math import ceil
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from app.models.pipeline import ProjectPipeline
from app.models.pipeline_log import PipelineLog
from app.models.article import Article
from app.schemas.pipeline import PipelineSettingsUpdate, PipelineSettingsPublic, PipelineLogPublic

logger = logging.getLogger(__name__)


def _parse_json_field(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _model_to_settings(pipe: ProjectPipeline) -> PipelineSettingsPublic:
    launch_hours = _parse_json_field(pipe.launch_hours, None) if pipe.launch_hours else None
    if isinstance(launch_hours, list) and all(isinstance(h, str) for h in launch_hours):
        pass
    else:
        launch_hours = None

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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    return _model_to_settings(pipe)


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
    return _model_to_settings(pipe)


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
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.services.idea_engine import generate_idea
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

                for i in range(daily_target):
                    try:
                        idea = generate_idea(
                            db=db,
                            project_id=project_id,
                            project_audience=project_audience,
                            project_language=project_language,
                            llm=llm,
                            search=search,
                        )
                        if idea:
                            ideas_generated += 1
                    except Exception as exc:
                        logger.exception("Pipeline idea generation failed")
                        errors.append(f"Idea {i + 1}: {exc}")

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
