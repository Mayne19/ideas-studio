import json
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from app.models.pipeline import ProjectPipeline
from app.models.pipeline_log import PipelineLog
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
    return PipelineSettingsPublic(
        id=pipe.id,
        project_id=pipe.project_id,
        enabled=pipe.enabled,
        active_days=_parse_json_field(pipe.active_days, []),
        launch_hour=pipe.launch_hour,
        articles_per_week=pipe.articles_per_week,
        category_priorities=_parse_json_field(pipe.category_priorities, {}),
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
    for field, value in update_dict.items():
        setattr(pipe, field, value)
    pipe.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pipe)
    return _model_to_settings(pipe)


def run_pipeline(db: Session, project_id: str) -> dict:
    from app.services.scheduler_service import run_daily_project_tasks

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
        result = run_daily_project_tasks(db, project_id)
        if result:
            ideas_generated = result.get("ideas_generated", 0)
            articles_created = result.get("articles_created", 0)
    except Exception as exc:
        logger.exception("Pipeline run failed for project %s", project_id)
        errors.append(str(exc))

    log_entry.status = "completed" if not errors else "failed"
    log_entry.ideas_generated = ideas_generated
    log_entry.articles_created = articles_created
    log_entry.errors = "\n".join(errors) if errors else None
    log_entry.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log_entry)

    return {"status": log_entry.status, "ideas_generated": ideas_generated, "articles_created": articles_created}


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
