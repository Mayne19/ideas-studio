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


def process_queue(db: Session, project_id: str, max_articles: int = 1) -> list[Article]:
    """Process the production queue. For articles with next_agent_key, runs the full orchestrator."""
    pending = (
        db.execute(
            select(Article)
            .where(
                Article.project_id == project_id,
                Article.status.in_(["writing_requested", "writing_in_progress", "draft_ready", "review_needed"]),
                Article.workflow_status.in_(["production", "quality"]),
            )
            .order_by(Article.priority.desc().nullslast(), Article.created_at.asc())
            .limit(max_articles)
        )
        .scalars()
        .all()
    )

    processed = []
    for article in pending:
        try:
            if article.next_agent_key:
                from app.services.seo.seo_generation_orchestrator import SEOGenerationOrchestrator
                from app.services.providers.llm_provider import get_llm_provider
                from app.services.providers.search_provider import get_search_provider

                llm = get_llm_provider()
                search = get_search_provider()
                orchestrator = SEOGenerationOrchestrator(db, project_id, llm, search)

                generated = orchestrator.generate_full_article(
                    preferred_title=article.title,
                    keyword=article.keyword,
                    category_id=article.category_id,
                    audience=article.audience,
                    angle=article.angle,
                    search_intent=article.search_intent,
                )

                if generated.status not in ("failed",):
                    for field in _FIELDS_TO_COPY:
                        val = getattr(generated, field, None)
                        if val is not None:
                            setattr(article, field, val)
                    article.status = "draft_ready"
                    article.workflow_status = "completed"
                    article.next_agent_key = None
                    article.updated_at = datetime.now(timezone.utc)
                    db.flush()
                    # Remove the temporary article created by the orchestrator
                    db.delete(generated)
                    db.flush()
                    log_step(
                        db, project_id,
                        f"Génération orchestrateur terminée : {article.title}",
                        level="info", step="production_queue", article_id=article.id,
                    )
                else:
                    log_step(
                        db, project_id,
                        f"Orchestrateur en échec pour {article.title}",
                        level="error", step="production_queue", article_id=article.id,
                    )
                processed.append(article)
            else:
                advanced = advance_workflow(db, article)
                processed.append(advanced)
        except Exception as exc:
            logger.exception("Failed to process article %s in queue", article.id)
            log_step(
                db, project_id,
                f"Erreur de production pour {article.title}: {exc}",
                level="error", step="production_queue", article_id=article.id,
            )
    db.commit()
    for a in processed:
        db.refresh(a)
    return processed


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
