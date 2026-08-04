import json
from datetime import datetime, timezone
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import Pipeline, PipelineRun
from app.models.content import Article, Category
from app.models.reference import ArticleStatus, RunStatus, set_run_status
from app.schemas.pipeline import PipelineSettingsUpdate, PipelineSettingsPublic, PipelineLogPublic

logger = logging.getLogger(__name__)

ACTIVE_IDEA_STATUSES = (
    ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY, ArticleStatus.IDEA_REJECTED,
    ArticleStatus.OUTLINE_READY, ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS,
    ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.REVIEW_NEEDED,
    ArticleStatus.CORRECTION_NEEDED, ArticleStatus.SCHEDULED, ArticleStatus.PUBLISHED,
)

_PENDING_DRAFT_STATUSES = (ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.WRITING_IN_PROGRESS)

FINAL_PIPELINE_STATUSES = {"success", "partial_success", "failed"}

_RUN_STATUS_CODE = {
    RunStatus.QUEUED: "running",
    RunStatus.RUNNING: "running",
    RunStatus.SUCCEEDED: "success",
    RunStatus.FAILED: "failed",
    RunStatus.CANCELLED: "failed",
}


def _pipeline_status(expected_ideas: int, generated_ideas: int, raw_status: str | None = None) -> str:
    if raw_status == "running":
        return "running"
    if generated_ideas <= 0:
        return "failed"
    if expected_ideas > 0 and generated_ideas < expected_ideas:
        return "partial_success"
    return "success"


def _failed_categories(categories_processed: list[dict]) -> list[dict]:
    failed = []
    for category in categories_processed:
        expected = int(category.get("expected") or 0)
        generated = int(category.get("generated") or 0)
        errors = category.get("errors") if isinstance(category.get("errors"), list) else []
        if generated < expected:
            failed.append({
                "category_id": category.get("category_id"),
                "category_name": category.get("category_name"),
                "expected": expected,
                "generated": generated,
                "errors": errors,
            })
    return failed


def _summary_from_run(run: PipelineRun, run_summary: dict | None = None) -> dict:
    summary = run_summary or {}
    expected = int(summary.get("expected_ideas") or 0)
    generated = int(summary.get("generated_ideas") or run.ideas_generated or 0)
    categories = summary.get("categories_processed") if isinstance(summary.get("categories_processed"), list) else []
    failed_categories = summary.get("failed_categories") if isinstance(summary.get("failed_categories"), list) else _failed_categories(categories)
    errors = summary.get("errors") if isinstance(summary.get("errors"), list) else ([run.error] if run.error else [])
    status = _RUN_STATUS_CODE.get(run.status_reason_id, "running")
    if status not in ("running",):
        status = _pipeline_status(expected, generated, None) if status != "failed" or generated > 0 else "failed"
    return {
        "workflow_run_id": run.id,
        "status": status,
        "expected_ideas": expected,
        "generated_ideas": generated,
        "total_expected_ideas": expected,
        "total_generated_ideas": generated,
        "ideas_generated": run.ideas_generated,
        "articles_created": run.articles_created,
        "categories_processed": categories,
        "failed_categories": failed_categories,
        "errors": errors,
        "run_errors": errors,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _category_frequency_summary(db: Session, project_id: str) -> tuple[int, list[dict]]:
    categories = db.execute(
        select(Category)
        .where(Category.project_id == project_id)
        .order_by(Category.priority_score.desc().nullslast(), Category.name.asc())
    ).scalars().all()
    rows = []
    total = 0
    for category in categories:
        enabled = category.is_pipeline_enabled is not False
        frequency = category.monthly_target
        if enabled and frequency:
            total += max(0, int(frequency))
        rows.append({
            "id": category.id,
            "name": category.name,
            "monthly_frequency": frequency,
            "pipeline_enabled": enabled,
            "priority": float(category.priority_score) if category.priority_score is not None else 0,
        })
    return total, rows


def _category_monthly_frequency(category: Category) -> int:
    try:
        return max(0, int(category.monthly_target or 0))
    except (TypeError, ValueError):
        return 0


def _active_pipeline_categories(db: Session, project_id: str) -> list[Category]:
    categories = db.execute(
        select(Category)
        .where(Category.project_id == project_id)
        .order_by(Category.priority_score.desc().nullslast(), Category.name.asc())
    ).scalars().all()
    return [c for c in categories if c.is_pipeline_enabled is not False and _category_monthly_frequency(c) > 0]


def _normalize_topic(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9àâäéèêëîïôöùûüçñ]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _topic_signature(db: Session, article: Article) -> tuple[str, str]:
    from app.services.article_service import primary_keyword
    title = article.current_revision.title if article.current_revision else ""
    return (_normalize_topic(title), _normalize_topic(primary_keyword(db, article.id)))


def _existing_topic_signatures(db: Session, project_id: str, category_id: str) -> set[tuple[str, str]]:
    existing = db.execute(
        select(Article).where(
            Article.project_id == project_id,
            Article.category_id == category_id,
            Article.status_reason_id.in_(ACTIVE_IDEA_STATUSES),
        )
    ).scalars().all()
    return {_topic_signature(db, article) for article in existing}


def _looks_duplicate(db: Session, article: Article, signatures: set[tuple[str, str]]) -> bool:
    title, keyword = _topic_signature(db, article)
    if not title and not keyword:
        return False
    for existing_title, existing_keyword in signatures:
        if keyword and existing_keyword and keyword == existing_keyword:
            return True
        if title and existing_title and title == existing_title:
            return True
    return False


def _category_context(category: Category, slot: int, frequency: int, duplicate_titles: list[str]) -> str:
    overrides = category.overrides or {}
    lines = [
        "Génération pipeline mensuelle par catégorie.",
        f"Catégorie obligatoire: {category.name}",
        f"category_id obligatoire: {category.id}",
        f"slug: {category.slug}",
        f"unité de fréquence: {slot}/{frequency}",
        "Crée une idée unique pour cette catégorie. Ne choisis pas une autre catégorie.",
    ]
    if category.description:
        lines.append(f"description: {category.description}")
    if overrides.get("editorial_goal"):
        lines.append(f"objectif éditorial: {overrides['editorial_goal']}")
    if overrides.get("target_audience"):
        lines.append(f"audience catégorie: {overrides['target_audience']}")
    if overrides.get("internal_notes"):
        lines.append(f"notes internes: {overrides['internal_notes']}")
    wc_min = overrides.get("word_count_min")
    wc_max = overrides.get("word_count_max")
    if wc_min or wc_max:
        lines.append(f"longueur cible catégorie: {wc_min or 'min non défini'}-{wc_max or 'max non défini'} mots")
    if duplicate_titles:
        lines.append("Sujets déjà présents à éviter strictement:")
        lines.extend(f"- {title}" for title in duplicate_titles[-8:])
    return "\n".join(lines)


def _model_to_settings(pipe: Pipeline, db: Session | None = None) -> PipelineSettingsPublic:
    schedule = pipe.schedule or {}
    total_monthly = None
    categories_frequencies = []
    if db is not None:
        total_monthly, categories_frequencies = _category_frequency_summary(db, pipe.project_id)

    return PipelineSettingsPublic(
        project_id=pipe.project_id,
        enabled=pipe.is_enabled,
        active_days=schedule.get("active_days", []),
        launch_hour=schedule.get("launch_hour", 8),
        ideas_frequency=schedule.get("ideas_frequency", "monthly"),
        launch_day=schedule.get("launch_day"),
        ideas_day_of_month=schedule.get("ideas_day_of_month"),
        publish_hour_start=schedule.get("publish_hour_start", 8),
        publish_hour_end=schedule.get("publish_hour_end", 10),
        articles_per_week=pipe.articles_per_week,
        category_priorities=schedule.get("category_priorities", {}),
        ideas_per_week=pipe.ideas_per_week,
        max_pending_drafts=pipe.max_pending_drafts,
        max_parallel_writing_jobs=pipe.max_parallel_jobs,
        paused_until=pipe.paused_until,
        paused_indefinitely=schedule.get("paused_indefinitely", False),
        default_quality_mode=pipe.quality_mode,
        launch_hours=schedule.get("launch_hours"),
        cost_limit_per_article_eur=float(pipe.cost_limit_per_article) if pipe.cost_limit_per_article is not None else None,
        total_monthly_from_categories=total_monthly,
        categories_frequencies=categories_frequencies,
        automation_notes="Worker automatique APScheduler disponible seulement si le processus worker est lance. Le lancement manuel reste disponible.",
        updated_at=pipe.updated_at,
    )


def get_or_create_pipeline(db: Session, project_id: str) -> Pipeline:
    pipe = db.get(Pipeline, project_id)
    if pipe:
        return pipe
    pipe = Pipeline(project_id=project_id)
    db.add(pipe)
    db.commit()
    db.refresh(pipe)
    return pipe


def get_pipeline(db: Session, project_id: str) -> PipelineSettingsPublic | None:
    pipe = db.get(Pipeline, project_id)
    if not pipe:
        total_monthly, categories_freqs = _category_frequency_summary(db, project_id)
        return PipelineSettingsPublic(
            project_id=project_id,
            enabled=False,
            active_days=[],
            launch_hour=8,
            ideas_frequency="monthly",
            launch_day=None,
            ideas_day_of_month=None,
            publish_hour_start=8,
            publish_hour_end=10,
            articles_per_week=5,
            category_priorities={},
            ideas_per_week=5,
            max_pending_drafts=10,
            paused_until=None,
            paused_indefinitely=False,
            default_quality_mode="quality",
            launch_hours=None,
            cost_limit_per_article_eur=None,
            total_monthly_from_categories=total_monthly,
            categories_frequencies=categories_freqs,
            automation_notes="Pipeline non créé. Configurez-le avant automatisation ; lancement manuel disponible après création.",
            updated_at=datetime.now(timezone.utc),
        )
    return _model_to_settings(pipe, db=db)


_SCHEDULE_FIELDS = {
    "active_days", "launch_hour", "ideas_frequency", "launch_day", "ideas_day_of_month",
    "publish_hour_start", "publish_hour_end", "category_priorities", "launch_hours",
    "paused_indefinitely",
}
_PIPELINE_FIELD_MAP = {
    "enabled": "is_enabled",
    "articles_per_week": "articles_per_week",
    "ideas_per_week": "ideas_per_week",
    "max_pending_drafts": "max_pending_drafts",
    "max_parallel_writing_jobs": "max_parallel_jobs",
    "paused_until": "paused_until",
    "default_quality_mode": "quality_mode",
    "cost_limit_per_article_eur": "cost_limit_per_article",
}


def update_pipeline(db: Session, project_id: str, data: PipelineSettingsUpdate) -> PipelineSettingsPublic:
    pipe = get_or_create_pipeline(db, project_id)
    update_dict = data.model_dump(exclude_unset=True)

    schedule = dict(pipe.schedule or {})
    for field in _SCHEDULE_FIELDS:
        if field in update_dict:
            value = update_dict.pop(field)
            if value is None:
                schedule.pop(field, None)
            else:
                schedule[field] = value
    pipe.schedule = schedule

    for field, value in update_dict.items():
        model_field = _PIPELINE_FIELD_MAP.get(field)
        if model_field:
            setattr(pipe, model_field, value)

    pipe.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pipe)
    return _model_to_settings(pipe, db=db)


def _count_pending_drafts(db: Session, project_id: str) -> int:
    return db.execute(
        select(func.count()).select_from(Article).where(
            Article.project_id == project_id,
            Article.status_reason_id.in_(_PENDING_DRAFT_STATUSES),
        )
    ).scalar_one()


def _is_paused(pipe: Pipeline) -> bool:
    schedule = pipe.schedule or {}
    if schedule.get("paused_indefinitely"):
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
    from app.services.article_service import primary_keyword
    from app.models.core import Project

    logger.info("Pipeline run start project=%s mode=%s", project_id, settings.PIPELINE_MODE)
    pipe = get_or_create_pipeline(db, project_id)
    project = db.get(Project, project_id)
    profile = project.active_editorial_profile if project else None

    running_run = db.execute(
        select(PipelineRun).where(
            PipelineRun.project_id == project_id,
            PipelineRun.status_reason_id.in_((RunStatus.QUEUED, RunStatus.RUNNING)),
            PipelineRun.finished_at.is_(None),
        ).order_by(PipelineRun.started_at.desc())
    ).scalars().first()
    if running_run:
        logger.info("Pipeline run already active project=%s run_id=%s", project_id, running_run.id)
        payload = _summary_from_run(running_run)
        payload["pipeline_mode"] = settings.PIPELINE_MODE
        return payload

    run = PipelineRun(project_id=project_id, started_at=datetime.now(timezone.utc))
    set_run_status(run, RunStatus.RUNNING)
    db.add(run)
    db.flush()

    errors = []
    ideas_generated = 0
    articles_created = 0
    pipeline_mode = settings.PIPELINE_MODE
    categories_processed: list[dict] = []
    generated_idea_ids: list[str] = []
    total_expected_ideas = 0
    critical_failure = False

    try:
        if _is_paused(pipe):
            errors.append("Pipeline is paused")
        else:
            max_drafts = pipe.max_pending_drafts or 10
            pending = _count_pending_drafts(db, project_id)
            if pending >= max_drafts:
                errors.append(f"Max pending drafts reached ({pending}/{max_drafts})")
            else:
                llm = get_llm_provider(project_id=project_id)
                logger.info(
                    "Pipeline provider loaded project=%s provider=%s model=%s is_mock=%s",
                    project_id, llm.provider_name, llm.model_name, llm.is_mock,
                )
                search = get_search_provider()
                agent_router = get_agent_router(db=db)

                project_audience = profile.audience if profile else None
                project_language = project.locale.split("-")[0] if project and project.locale else "fr"
                active_categories = _active_pipeline_categories(db, project_id)
                total_expected_ideas = sum(_category_monthly_frequency(category) for category in active_categories)

                if not active_categories or total_expected_ideas <= 0:
                    errors.append("Aucune catégorie active avec volume mensuel configuré.")

                # Phase 1: Generate ideas (always)
                for category in active_categories:
                    frequency = _category_monthly_frequency(category)
                    category_report = {
                        "category_id": category.id,
                        "category_name": category.name,
                        "expected": frequency,
                        "generated": 0,
                        "errors": [],
                    }
                    signatures = _existing_topic_signatures(db, project_id, category.id)
                    from app.models.content import ArticleRevision
                    category_titles = [
                        title for title, in db.execute(
                            select(ArticleRevision.title)
                            .join(Article, Article.current_revision_id == ArticleRevision.id)
                            .where(
                                Article.project_id == project_id,
                                Article.category_id == category.id,
                                Article.status_reason_id.in_(ACTIVE_IDEA_STATUSES),
                            )
                            .order_by(Article.created_at.desc())
                            .limit(12)
                        ).all()
                        if title
                    ]
                    for slot in range(1, frequency + 1):
                        created = None
                        for attempt in range(1, 4):
                            try:
                                idea = generate_idea(
                                    db=db,
                                    project_id=project_id,
                                    project_audience=project_audience,
                                    project_language=project_language,
                                    llm=llm,
                                    search=search,
                                    context_hint=_category_context(category, slot, frequency, category_titles),
                                    keyword=f"{category.name} idee {slot}" if llm.is_mock else None,
                                    category_id=category.id,
                                    audience=(category.overrides or {}).get("target_audience") or project_audience,
                                    agent_router=agent_router,
                                )
                                if not idea:
                                    category_report["errors"].append(f"Idée {slot}: doublon ou proposition inexploitable (tentative {attempt}).")
                                    continue
                                if not idea.category_id:
                                    idea.category_id = category.id
                                if _looks_duplicate(db, idea, signatures):
                                    db.delete(idea)
                                    db.flush()
                                    category_report["errors"].append(f"Idée {slot}: doublon détecté (tentative {attempt}).")
                                    continue

                                signatures.add(_topic_signature(db, idea))
                                idea_title = idea.current_revision.title if idea.current_revision else ""
                                category_titles.append(idea_title)
                                generated_idea_ids.append(idea.id)
                                ideas_generated += 1
                                category_report["generated"] += 1
                                created = idea
                                break
                            except Exception as exc:
                                logger.exception("Pipeline idea generation failed category=%s slot=%s attempt=%s", category.id, slot, attempt)
                                category_report["errors"].append(f"Idée {slot}: {exc}")
                        if created is None:
                            errors.append(f"{category.name}: idée {slot}/{frequency} non générée.")
                    categories_processed.append(category_report)

                # Phase 2: Generate briefs / full drafts based on pipeline mode
                if pipeline_mode in ("brief_only", "draft_generation") and ideas_generated > 0:
                    from app.services.seo.seo_generation_orchestrator import generate_full_article

                    pending_ideas = db.execute(
                        select(Article).where(
                            Article.project_id == project_id,
                            Article.status_reason_id == ArticleStatus.IDEA_PROPOSED,
                            Article.id.in_(generated_idea_ids),
                        ).order_by(Article.opportunity_score.desc().nullslast())
                    ).scalars().all()
                    for idea in pending_ideas:
                        try:
                            idea_title = idea.current_revision.title if idea.current_revision else ""
                            article = generate_full_article(
                                db=db,
                                project_id=project_id,
                                llm=llm,
                                search=search,
                                preferred_title=idea_title,
                                keyword=primary_keyword(db, idea.id),
                                category_id=idea.category_id,
                                search_intent=idea.search_intent,
                                agent_router=agent_router,
                                existing_article_id=idea.id,
                            )
                            articles_created += 1
                        except Exception as exc:
                            logger.exception("Pipeline article generation failed")
                            errors.append(f"Article from idea {idea.id}: {exc}")
    except Exception as exc:
        logger.exception("Pipeline run failed for project %s", project_id)
        errors.append(str(exc))
        critical_failure = True

    run.ideas_generated = ideas_generated
    run.articles_created = articles_created
    failed_categories = _failed_categories(categories_processed)
    final_ok = not (critical_failure and ideas_generated == 0)
    set_run_status(run, RunStatus.SUCCEEDED if final_ok else RunStatus.FAILED)
    run.error = "; ".join(errors)[:2000] if errors else None
    run.finished_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to persist pipeline run for project %s", project_id)
        db.rollback()
        db.add(run)
        db.commit()
    db.refresh(run)

    run_summary = {
        "expected_ideas": total_expected_ideas,
        "generated_ideas": ideas_generated,
        "categories_processed": categories_processed,
        "failed_categories": failed_categories,
        "errors": errors,
    }
    payload = _summary_from_run(run, run_summary)
    payload["pipeline_mode"] = pipeline_mode
    return payload


def list_pipeline_logs(db: Session, project_id: str, limit: int = 20) -> list[PipelineLogPublic]:
    runs = db.execute(
        select(PipelineRun)
        .where(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    ).scalars().all()
    items = []
    for run in runs:
        summary = _summary_from_run(run)
        items.append(PipelineLogPublic(
            id=run.id,
            project_id=run.project_id,
            status=summary["status"],
            workflow_run_id=summary["workflow_run_id"],
            expected_ideas=summary["expected_ideas"],
            generated_ideas=summary["generated_ideas"],
            failed_categories=summary["failed_categories"],
            run_errors=summary["run_errors"],
            ideas_generated=run.ideas_generated,
            articles_created=run.articles_created,
            errors=run.error,
            started_at=run.started_at,
            finished_at=run.finished_at,
        ))
    return items
