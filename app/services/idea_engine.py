import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.article import Article
from app.services.providers.llm_provider import LLMProvider
from app.services.providers.search_provider import SearchProvider
from app.services.log_service import log_step


_MOCK_IDEA_TEMPLATES = [
    {
        "title": "Comment optimiser votre stratégie de contenu SEO en {year}",
        "keyword": "stratégie contenu SEO",
        "angle": "Guide pratique avec étapes concrètes",
        "search_intent": "informational",
        "audience": "Marketeurs et blogueurs débutants",
    },
    {
        "title": "Les meilleures pratiques pour accélérer votre site web",
        "keyword": "optimisation vitesse site web",
        "angle": "Checklist technique actionnable",
        "search_intent": "informational",
        "audience": "Développeurs web",
    },
    {
        "title": "Guide complet : créer un blog rentable en partant de zéro",
        "keyword": "créer blog rentable",
        "angle": "Étapes détaillées du débutant à l'expert",
        "search_intent": "informational",
        "audience": "Entrepreneurs en ligne",
    },
]

_mock_template_index = 0


def _next_mock_idea(project_audience: str | None) -> dict:
    global _mock_template_index
    tpl = _MOCK_IDEA_TEMPLATES[_mock_template_index % len(_MOCK_IDEA_TEMPLATES)]
    _mock_template_index += 1
    year = datetime.now(timezone.utc).year
    return {
        "title": tpl["title"].format(year=year),
        "keyword": tpl["keyword"],
        "angle": tpl["angle"],
        "search_intent": tpl["search_intent"],
        "audience": project_audience or tpl["audience"],
        "opportunity_score": 0.75,
        "serp_summary": {"mock": True, "top_results": []},
    }


def _keyword_already_active(db: Session, project_id: str, keyword: str) -> bool:
    active_statuses = {
        "idea_proposed", "idea_priority", "outline_ready", "writing_requested",
        "writing_in_progress", "draft", "draft_ready", "review_needed",
        "correction_needed", "scheduled", "published",
    }
    stmt = (
        select(Article)
        .where(
            Article.project_id == project_id,
            Article.keyword == keyword,
            Article.status.in_(active_statuses),
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def generate_idea(
    db: Session,
    project_id: str,
    project_audience: str | None,
    project_language: str,
    llm: LLMProvider,
    search: SearchProvider,
    context_hint: str | None = None,
    preferred_title: str | None = None,
) -> Article | None:
    if llm.is_mock:
        idea_data = _next_mock_idea(project_audience)
    else:
        query = context_hint or f"idées d'articles SEO pour {project_audience or 'un blog'} en {project_language}"
        search_results = search.search(query, limit=5)
        serp_snippets = "\n".join(f"- {r.title}: {r.snippet}" for r in search_results)

        schema_hint = '{"title": "...", "keyword": "...", "angle": "...", "search_intent": "informational|commercial|transactional|navigational", "audience": "..."}'
        prompt = (
            f"Génère une idée d'article SEO originale pour un blog en langue '{project_language}'.\n"
            f"Audience cible : {project_audience or 'grand public'}.\n"
            f"Contexte SERP actuel :\n{serp_snippets}\n\n"
            f"Réponds uniquement en JSON."
        )
        idea_data = llm.generate_json(prompt, schema_hint=schema_hint)
        if not idea_data.get("keyword"):
            log_step(db, project_id, "LLM n'a pas retourné de keyword valide", level="warning", step="generate_idea")
            return None

        idea_data["opportunity_score"] = min(1.0, len(search_results) / 10.0 + 0.3)
        idea_data["serp_summary"] = {"top_results": [{"title": r.title, "url": r.url} for r in search_results]}

    keyword = idea_data.get("keyword", "").strip()
    if not keyword:
        return None

    if _keyword_already_active(db, project_id, keyword):
        log_step(db, project_id, f"Idée ignorée (keyword déjà actif) : {keyword}", level="info", step="generate_idea")
        return None

    generated_title = idea_data.get("title", keyword)
    final_title = preferred_title or generated_title

    article = Article(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=final_title,
        slug=f"idea-{uuid.uuid4().hex[:8]}",
        keyword=keyword,
        angle=idea_data.get("angle"),
        search_intent=idea_data.get("search_intent"),
        audience=idea_data.get("audience"),
        opportunity_score=idea_data.get("opportunity_score", 0.5),
        serp_summary_json=json.dumps(idea_data.get("serp_summary", {})),
        status="idea_proposed",
        priority=0,
        word_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(article)
    log_step(db, project_id, f"Idée générée : {article.title}", level="info", step="generate_idea", article_id=article.id)
    db.flush()
    return article
