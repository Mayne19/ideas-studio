import json
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.article import Article
from app.services.log_service import log_step

logger = logging.getLogger(__name__)

# Agent pipeline order for production
PRODUCTION_AGENTS = [
    "intent_analyzer",
    "research_brief_writer",
    "keyword_brief_writer",
    "editorial_angle_planner",
    "outline_planner",
    "content_writer",
    "title_generator",
    "meta_description_writer",
    "faq_generator",
    "callout_planner",
    "image_selector",
    "internal_link_builder",
    "external_link_finder",
    "language_quality",
    "originality_check",
    "humanization",
    "eeat_check",
    "editorial_quality_gate",
    "seo_final_checklist",
]

PLANNING_AGENTS = [
    "idea_generator",
    "intent_analyzer",
    "research_brief_writer",
    "keyword_brief_writer",
    "editorial_angle_planner",
    "outline_planner",
]


def _parse_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _to_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def compute_next_agent(article: Article) -> str | None:
    """Determine the next agent to run based on completed agents and available JSON fields."""
    completed = _parse_json_list(article.completed_agent_keys)
    json_field_map = {
        "intent_analyzer": article.intent_analysis_json,
        "research_brief_writer": article.research_brief_json,
        "keyword_brief_writer": article.keyword_brief_json,
        "editorial_angle_planner": article.editorial_angle_json,
        "outline_planner": article.outline_json,
    }

    for agent_key in PRODUCTION_AGENTS:
        if agent_key not in completed:
            # Check if this agent's output already exists (e.g., from orchestrator)
            if agent_key in json_field_map and json_field_map[agent_key] is not None:
                completed.append(agent_key)
                continue
            return agent_key
    return None


def advance_workflow(db: Session, article: Article) -> Article:
    """Mark the current agent as complete and set the next agent."""
    completed = _parse_json_list(article.completed_agent_keys)

    if article.next_agent_key and article.next_agent_key not in completed:
        completed.append(article.next_agent_key)

    article.completed_agent_keys = _to_json(completed)

    next_agent = compute_next_agent(article)
    article.next_agent_key = next_agent

    if next_agent is None:
        article.workflow_status = "completed"
        if article.status not in ("published", "scheduled"):
            article.status = "draft_ready"
    elif next_agent in ("content_writer", "title_generator"):
        article.workflow_status = "production"
        if article.status in ("idea_proposed", "idea_priority"):
            article.status = "writing_in_progress"
    elif next_agent in ("language_quality", "originality_check", "humanization", "eeat_check",
                        "editorial_quality_gate", "seo_final_checklist"):
        article.workflow_status = "quality"
        if article.status == "writing_in_progress":
            article.status = "draft_ready"

    article.updated_at = datetime.now(timezone.utc)
    db.flush()
    return article


def send_to_production(db: Session, article_id: str) -> Article | None:
    """Move an idea into the production queue and start agent workflow."""
    article = db.get(Article, article_id)
    if not article:
        return None
    if article.status not in ("idea_proposed", "idea_priority"):
        logger.warning("Article %s has status %s, cannot send to production", article_id, article.status)
        return None

    completed = _parse_json_list(article.completed_agent_keys)
    if "idea_generator" not in completed:
        completed.append("idea_generator")

    next_agent = compute_next_agent(article)
    article.completed_agent_keys = _to_json(completed)
    article.next_agent_key = next_agent
    article.workflow_status = "production"
    article.status = "writing_requested"
    article.workflow_run_id = article.workflow_run_id or str(uuid.uuid4())
    article.updated_at = datetime.now(timezone.utc)

    log_step(
        db, article.project_id,
        f"Idée envoyée en production : {article.title} (prochain agent : {next_agent})",
        level="info", step="send_to_production", article_id=article.id,
    )
    db.flush()
    return article


_FIELDS_TO_COPY = [
    "content", "word_count", "reading_time_minutes", "meta_title", "meta_description",
    "excerpt", "faq_json", "slug", "outline_json", "keyword_brief_json",
    "intent_analysis_json", "editorial_angle_json", "research_brief_json",
    "image_plan_json", "callout_plan_json", "internal_links_json", "external_links_json",
    "language_quality_report_json", "originality_report_json", "humanization_report_json",
    "eeat_checklist_json", "editorial_quality_report_json", "seo_final_checklist_json",
    "generation_report_json", "seo_review_json", "fact_check_report_json",
    "geo_optimization_json", "structured_data_json", "cannibalization_outline_json",
    "global_score", "seo_score", "quality_score", "eeat_score", "readability_score",
]


WRITING_STALE_MINUTES = 30


def requeue_stale_writing(db: Session, project_id: str, minutes: int = WRITING_STALE_MINUTES) -> int:
    """Remet en file les rédactions bloquées (writing_in_progress sans update depuis X minutes)."""
    from datetime import timedelta
    threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stale = (
        db.query(Article)
        .filter(
            Article.project_id == project_id,
            Article.status == "writing_in_progress",
            Article.updated_at < threshold,
        )
        .all()
    )
    for article in stale:
        article.status = "writing_requested"
        article.workflow_status = "production"
        article.updated_at = datetime.now(timezone.utc)
        log_step(
            db, project_id,
            f"Rédaction bloquée depuis plus de {minutes} min, remise en file : {article.title}",
            level="warning", step="writing_queue", article_id=article.id,
        )
    if stale:
        db.commit()
    return len(stale)


def claim_for_writing(db: Session, project_id: str, limit: int) -> list[str]:
    """Réclame atomiquement jusqu'à `limit` idées en file (writing_requested -> writing_in_progress).

    Le claim par UPDATE conditionnel garantit qu'aucun article n'est pris
    par deux workers en même temps.
    """
    candidate_ids = (
        db.execute(
            select(Article.id)
            .where(
                Article.project_id == project_id,
                Article.status == "writing_requested",
                Article.workflow_status == "production",
            )
            .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    claimed: list[str] = []
    for article_id in candidate_ids:
        updated = (
            db.query(Article)
            .filter(Article.id == article_id, Article.status == "writing_requested")
            .update(
                {"status": "writing_in_progress", "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        )
        if updated:
            claimed.append(article_id)
    db.commit()
    return claimed


def write_queued_article(article_id: str, project_id: str) -> dict:
    """Rédige un article réclamé, dans sa propre session (exécutable en thread parallèle)."""
    from app.core.database import SessionLocal
    from app.services.providers.llm_provider import get_llm_provider, ProviderUnavailableError
    from app.services.providers.search_provider import get_search_provider
    from app.services.agents.agent_router import get_agent_router
    from app.services.seo.seo_generation_orchestrator import generate_full_article

    db = SessionLocal()
    try:
        article = db.get(Article, article_id)
        if not article:
            return {"id": article_id, "status": "not_found"}
        title = article.title
        try:
            llm = get_llm_provider(project_id=project_id)
            search = get_search_provider()
            generate_full_article(
                db=db,
                project_id=project_id,
                llm=llm,
                search=search,
                agent_router=get_agent_router(db=db),
                preferred_title=article.title,
                keyword=article.keyword,
                category_id=article.category_id,
                audience=article.audience,
                angle=article.angle,
                search_intent=article.search_intent,
                existing_article_id=article_id,
            )
            db.commit()
            db.refresh(article)
            log_step(
                db, project_id,
                f"Rédaction terminée ({article.status}) : {title}",
                level="info" if article.status != "failed" else "error",
                step="writing_queue", article_id=article_id,
            )
            db.commit()
            return {"id": article_id, "status": article.status}
        except ProviderUnavailableError as exc:
            db.rollback()
            article = db.get(Article, article_id)
            if article:
                # Pas d'échec définitif : provider indisponible, on remet en file
                article.status = "writing_requested"
                article.updated_at = datetime.now(timezone.utc)
                log_step(
                    db, project_id,
                    f"Provider IA indisponible, rédaction remise en file : {title} ({exc})",
                    level="warning", step="writing_queue", article_id=article_id,
                )
                db.commit()
            return {"id": article_id, "status": "requeued", "error": str(exc)}
        except Exception as exc:
            logger.exception("Writing job failed for article %s", article_id)
            db.rollback()
            article = db.get(Article, article_id)
            if article:
                article.status = "failed"
                article.workflow_status = "error"
                article.updated_at = datetime.now(timezone.utc)
                log_step(
                    db, project_id,
                    f"Rédaction échouée : {title} — {exc}",
                    level="error", step="writing_queue", article_id=article_id,
                )
                db.commit()
            return {"id": article_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


def resolve_max_parallel(db: Session, project_id: str) -> int:
    from app.models.pipeline import ProjectPipeline
    pipe = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()
    value = pipe.max_parallel_writing_jobs if pipe and pipe.max_parallel_writing_jobs else 3
    return max(1, min(int(value), 10))


def process_writing_queue(db: Session, project_id: str, max_parallel: int | None = None) -> dict:
    """Draine la file de rédaction : claim + rédactions en parallèle (bornées)."""
    from app.core.database import engine

    if max_parallel is None:
        max_parallel = resolve_max_parallel(db, project_id)
    # SQLite ne supporte pas les écritures concurrentes : on sérialise en dev
    if engine.dialect.name == "sqlite":
        max_parallel = 1

    requeued = requeue_stale_writing(db, project_id)
    claimed = claim_for_writing(db, project_id, max_parallel)

    results: list[dict] = []
    if claimed:
        log_step(
            db, project_id,
            f"File de rédaction : {len(claimed)} rédaction(s) lancée(s) (max parallèle : {max_parallel})",
            level="info", step="writing_queue",
        )
        db.commit()
        if len(claimed) == 1:
            results.append(write_queued_article(claimed[0], project_id))
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_parallel) as pool:
                results = list(pool.map(lambda aid: write_queued_article(aid, project_id), claimed))
    return {"requeued_stale": requeued, "claimed": len(claimed), "results": results}


def process_queue(db: Session, project_id: str, max_articles: int = 1) -> list[Article]:
    """Compat : draine la file via le nouveau mécanisme et retourne les articles traités."""
    outcome = process_writing_queue(db, project_id, max_parallel=max_articles)
    ids = [r["id"] for r in outcome["results"] if r.get("status") != "not_found"]
    if not ids:
        return []
    return db.query(Article).filter(Article.id.in_(ids)).all()


def get_queue_summary(db: Session, project_id: str) -> dict:
    """Get a summary of the production queue."""
    queue_statuses = ["writing_requested", "writing_in_progress", "draft_ready", "review_needed", "correction_needed"]
    counts = {}
    total = 0
    for status in queue_statuses:
        cnt = (
            db.query(Article)
            .filter(
                Article.project_id == project_id,
                Article.status == status,
                Article.workflow_status.in_(["production", "quality"]),
            )
            .count()
        )
        counts[status] = cnt
        total += cnt

    counts["failed"] = (
        db.query(Article)
        .filter(
            Article.project_id == project_id,
            Article.status == "failed",
            Article.workflow_status == "error",
        )
        .count()
    )

    next_up = (
        db.execute(
            select(Article)
            .where(
                Article.project_id == project_id,
                Article.status.in_(["writing_requested", "writing_in_progress"]),
                Article.workflow_status == "production",
            )
            .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
            .limit(1)
        )
        .scalars()
        .first()
    )

    return {
        "total_in_queue": total,
        "counts": counts,
        "next_up": {
            "id": next_up.id,
            "title": next_up.title,
            "next_agent_key": next_up.next_agent_key,
        } if next_up else None,
    }
