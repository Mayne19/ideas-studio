import json
from datetime import datetime, timezone
import logging
import re
from sqlalchemy.orm import Session
from app.models.pipeline import ProjectPipeline
from app.models.pipeline_log import PipelineLog
from app.models.article import Article
from app.models.category import Category
from app.schemas.pipeline import PipelineSettingsUpdate, PipelineSettingsPublic, PipelineLogPublic

logger = logging.getLogger(__name__)

ACTIVE_IDEA_STATUSES = {
    "idea_proposed",
    "idea_priority",
    "idea_rejected",
    "outline_ready",
    "writing_requested",
    "writing_in_progress",
    "draft",
    "draft_ready",
    "review_needed",
    "correction_needed",
    "scheduled",
    "published",
}

FINAL_PIPELINE_STATUSES = {"success", "partial_success", "failed"}


def _parse_json_field(value: str | None, default):
    if not value:
        return default
    try:
        parsed = json.loads(value)
        return default if parsed is None else parsed
    except (json.JSONDecodeError, TypeError):
        return default


def _parse_json_object(value) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    current = value
    for _ in range(2):
        if not isinstance(current, str):
            break
        try:
            current = json.loads(current)
        except (json.JSONDecodeError, TypeError):
            return {}
    return current if isinstance(current, dict) else {}


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


def _summary_from_log(log: PipelineLog) -> dict:
    summary = _parse_json_object(log.errors)
    expected = int(summary.get("expected_ideas") or summary.get("total_expected_ideas") or 0)
    generated = int(summary.get("generated_ideas") or summary.get("total_generated_ideas") or log.ideas_generated or 0)
    categories = summary.get("categories_processed") if isinstance(summary.get("categories_processed"), list) else []
    failed_categories = summary.get("failed_categories") if isinstance(summary.get("failed_categories"), list) else _failed_categories(categories)
    errors = summary.get("errors") if isinstance(summary.get("errors"), list) else []
    status = log.status if log.status in FINAL_PIPELINE_STATUSES or log.status == "running" else _pipeline_status(expected, generated, log.status)
    return {
        "workflow_run_id": summary.get("workflow_run_id") or log.id,
        "status": status,
        "expected_ideas": expected,
        "generated_ideas": generated,
        "total_expected_ideas": expected,
        "total_generated_ideas": generated,
        "ideas_generated": log.ideas_generated,
        "articles_created": log.articles_created,
        "categories_processed": categories,
        "failed_categories": failed_categories,
        "errors": errors,
        "run_errors": errors,
        "started_at": log.started_at.isoformat(),
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }


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


def _category_monthly_frequency(category: Category) -> int:
    frequency = category.monthly_frequency if category.monthly_frequency is not None else category.target_frequency
    try:
        return max(0, int(frequency or 0))
    except (TypeError, ValueError):
        return 0


def _active_pipeline_categories(db: Session, project_id: str) -> list[Category]:
    return [
        category
        for category in (
            db.query(Category)
            .filter(Category.project_id == project_id)
            .order_by(Category.priority.desc(), Category.name.asc())
            .all()
        )
        if category.pipeline_enabled is not False and _category_monthly_frequency(category) > 0
    ]


def _normalize_topic(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9àâäéèêëîïôöùûüçñ]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _topic_signature(article: Article) -> tuple[str, str]:
    return (_normalize_topic(article.title), _normalize_topic(article.keyword))


def _existing_topic_signatures(db: Session, project_id: str, category_id: str) -> set[tuple[str, str]]:
    existing = (
        db.query(Article)
        .filter(
            Article.project_id == project_id,
            Article.category_id == category_id,
            Article.status.in_(ACTIVE_IDEA_STATUSES),
        )
        .all()
    )
    return {_topic_signature(article) for article in existing}


def _looks_duplicate(article: Article, signatures: set[tuple[str, str]]) -> bool:
    title, keyword = _topic_signature(article)
    if not title and not keyword:
        return False
    for existing_title, existing_keyword in signatures:
        if keyword and existing_keyword and keyword == existing_keyword:
            return True
        if title and existing_title and title == existing_title:
            return True
    return False


def _category_context(category: Category, slot: int, frequency: int, duplicate_titles: list[str]) -> str:
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
    if category.editorial_goal:
        lines.append(f"objectif éditorial: {category.editorial_goal}")
    if category.target_audience:
        lines.append(f"audience catégorie: {category.target_audience}")
    if category.internal_notes:
        lines.append(f"notes internes: {category.internal_notes}")
    if category.vertical:
        lines.append(f"vertical: {category.vertical}")
    if category.niche:
        lines.append(f"niche: {category.niche}")
    if category.word_count_min or category.word_count_max:
        lines.append(f"longueur cible catégorie: {category.word_count_min or 'min non défini'}-{category.word_count_max or 'max non défini'} mots")
    if duplicate_titles:
        lines.append("Sujets déjà présents à éviter strictement:")
        lines.extend(f"- {title}" for title in duplicate_titles[-8:])
    return "\n".join(lines)


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
        ideas_day_of_month=pipe.ideas_day_of_month,
        publish_hour_start=pipe.publish_hour_start if pipe.publish_hour_start is not None else 8,
        publish_hour_end=pipe.publish_hour_end if pipe.publish_hour_end is not None else 10,
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
        total_monthly, categories_freqs = _category_frequency_summary(db, project_id)
        return PipelineSettingsPublic(
            id="",
            project_id=project_id,
            enabled=False,
            active_days=[],
            launch_hour=8,
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

    logger.info("Pipeline run start project=%s mode=%s", project_id, settings.PIPELINE_MODE)
    pipe = get_or_create_pipeline(db, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    running_log = (
        db.query(PipelineLog)
        .filter(
            PipelineLog.project_id == project_id,
            PipelineLog.status == "running",
            PipelineLog.finished_at.is_(None),
        )
        .order_by(PipelineLog.started_at.desc())
        .first()
    )
    if running_log:
        logger.info("Pipeline run already active project=%s workflow_run_id=%s", project_id, running_log.id)
        payload = _summary_from_log(running_log)
        payload["pipeline_mode"] = settings.PIPELINE_MODE
        return payload

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
    workflow_run_id = log_entry.id
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

                project_audience = project.audience if project else None
                project_language = project.language if project else "fr"
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
                    category_titles = [
                        article.title
                        for article in (
                            db.query(Article.title)
                            .filter(
                                Article.project_id == project_id,
                                Article.category_id == category.id,
                                Article.status.in_(ACTIVE_IDEA_STATUSES),
                            )
                            .order_by(Article.created_at.desc())
                            .limit(12)
                            .all()
                        )
                        if article.title
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
                                    audience=category.target_audience or project_audience,
                                    agent_router=agent_router,
                                )
                                if not idea:
                                    category_report["errors"].append(f"Idée {slot}: doublon ou proposition inexploitable (tentative {attempt}).")
                                    continue
                                if not idea.category_id:
                                    idea.category_id = category.id
                                if _looks_duplicate(idea, signatures):
                                    db.delete(idea)
                                    db.flush()
                                    category_report["errors"].append(f"Idée {slot}: doublon détecté (tentative {attempt}).")
                                    continue

                                idea.workflow_run_id = workflow_run_id
                                idea.workflow_status = "idea_prebrief"
                                idea.completed_agent_keys = json.dumps(["idea_generator"], ensure_ascii=False)
                                idea.next_agent_key = "human_validation"
                                planning_brief = _parse_json_object(idea.planning_brief_json)
                                planning_brief.update({
                                    "workflow_run_id": workflow_run_id,
                                    "phase_current": "Idée / Pré-brief",
                                    "next_step": "Envoyer en production",
                                    "category_name": category.name,
                                    "category_slug": category.slug,
                                    "category_frequency_slot": slot,
                                    "category_monthly_frequency": frequency,
                                })
                                idea.planning_brief_json = planning_brief
                                db.flush()

                                signatures.add(_topic_signature(idea))
                                category_titles.append(idea.title)
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

                    pending_ideas = (
                        db.query(Article)
                        .filter(
                            Article.project_id == project_id,
                            Article.status == "idea_proposed",
                            Article.id.in_(generated_idea_ids),
                        )
                        .order_by(Article.opportunity_score.desc().nullslast())
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
    except Exception as exc:
        logger.exception("Pipeline run failed for project %s", project_id)
        errors.append(str(exc))
        critical_failure = True

    if generated_idea_ids:
        ideas_generated = (
            db.query(Article)
            .filter(
                Article.project_id == project_id,
                Article.workflow_run_id == workflow_run_id,
            )
            .count()
        )

    log_entry.ideas_generated = ideas_generated
    log_entry.articles_created = articles_created
    failed_categories = _failed_categories(categories_processed)
    final_status = "failed" if critical_failure and ideas_generated == 0 else _pipeline_status(total_expected_ideas, ideas_generated)
    log_entry.status = final_status
    run_summary = {
        "workflow_run_id": workflow_run_id,
        "status": final_status,
        "expected_ideas": total_expected_ideas,
        "generated_ideas": ideas_generated,
        "total_expected_ideas": total_expected_ideas,
        "total_generated_ideas": ideas_generated,
        "categories_processed": categories_processed,
        "failed_categories": failed_categories,
        "errors": errors,
    }
    log_entry.errors = json.dumps(run_summary, ensure_ascii=False)
    log_entry.finished_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        # Session invalidée par l'échec du run : rollback puis ré-insérer le log seul
        logger.exception("Failed to persist pipeline log for project %s", project_id)
        db.rollback()
        db.add(log_entry)
        db.commit()
    db.refresh(log_entry)

    payload = _summary_from_log(log_entry)
    payload["pipeline_mode"] = pipeline_mode
    return payload


def list_pipeline_logs(db: Session, project_id: str, limit: int = 20) -> list[PipelineLogPublic]:
    logs = (
        db.query(PipelineLog)
        .filter(PipelineLog.project_id == project_id)
        .order_by(PipelineLog.started_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for log in logs:
        summary = _summary_from_log(log)
        items.append(PipelineLogPublic(
            id=log.id,
            project_id=log.project_id,
            status=summary["status"],
            workflow_run_id=summary["workflow_run_id"],
            expected_ideas=summary["expected_ideas"],
            generated_ideas=summary["generated_ideas"],
            failed_categories=summary["failed_categories"],
            run_errors=summary["run_errors"],
            ideas_generated=log.ideas_generated,
            articles_created=log.articles_created,
            errors=log.errors,
            started_at=log.started_at,
            finished_at=log.finished_at,
        ))
    return items
