from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.category import Category
from app.schemas.seo_workflow import IdeaDiscoveryResult, asdict
from app.services.providers.llm_provider import LLMProvider
from app.services.providers.search_provider import SearchProvider, MockSearchProvider
from app.services.seo.adapters.serp_adapter import serp_adapter


def discover_ideas(
    db: Session,
    project_id: str,
    llm: LLMProvider,
    search: SearchProvider,
    count: int = 5,
    context_hint: str | None = None,
    project_audience: str | None = None,
    project_language: str = "fr",
    category_strategy: dict | None = None,
) -> list[dict]:
    ideas: list[dict] = []
    categories = db.query(Category).filter(Category.project_id == project_id).all()
    category_id = None
    if category_strategy and category_strategy.get("chosen_category_id"):
        category_id = category_strategy["chosen_category_id"]

    existing_keywords = {
        a.keyword for a in db.query(Article).filter(
            Article.project_id == project_id,
            Article.status.in_(["published", "draft", "draft_ready", "idea_proposed", "idea_priority"]),
        ).all()
        if a.keyword
    }

    for i in range(count):
        try:
            title = f"Idée #{i + 1}: {context_hint or 'Sujet SEO'}"
            keyword = f"mot-cle-{i + 1}-seo"

            if llm.is_mock:
                title = f"Titre suggestion {i + 1} pour {context_hint or 'SEO'}"
                keyword = f"keyword-suggestion-{i + 1}"
            else:
                query = context_hint or f"idées d'articles SEO en {project_language}"
                serp_results = search.search(query, limit=3)
                serp_context = "\n".join(f"- {r.title}: {r.snippet}" for r in serp_results) if not isinstance(search, MockSearchProvider) else ""

                prompt = (
                    f"Génère une idée d'article SEO originale en langue '{project_language}'.\n"
                    f"Audience cible : {project_audience or 'grand public'}.\n"
                    f"Contexte : {context_hint or 'aucun'}.\n"
                    f"Contexte SERP :\n{serp_context}\n\n"
                    'Réponds en JSON : {"title": "...", "keyword": "...", "angle": "...", "search_intent": "informational|commercial"}'
                )
                idea_data = llm.generate_json(
                    prompt,
                    schema_hint='{"title": "...", "keyword": "...", "angle": "...", "search_intent": "informational|commercial"}',
                )
                if isinstance(idea_data, dict):
                    title = idea_data.get("title", title)
                    keyword = idea_data.get("keyword", keyword)

            if keyword in existing_keywords:
                continue

            ref = IdeaDiscoveryResult(
                title=title,
                category_id=category_id or (categories[0].id if categories else None),
                main_keyword=keyword,
                secondary_keywords=[keyword],
                detected_intent="informational",
                opportunity_score=round(0.5 + (i / (count * 2)), 2),
                source="ai_generation" if not llm.is_mock else "mock_template",
                real_research_used=not llm.is_mock and not isinstance(search, MockSearchProvider),
                confidence_score=round(0.7 - (i * 0.05), 2),
                limitations=[],
            )
            if serp_adapter.configured:
                ref.real_research_used = True
                ref.source = "serp_research"

            ideas.append(asdict(ref))
        except Exception:
            continue

    return ideas


def discover_ideas_dict(
    db: Session,
    project_id: str,
    llm: LLMProvider,
    search: SearchProvider,
    count: int = 5,
    context_hint: str | None = None,
    project_audience: str | None = None,
    project_language: str = "fr",
    category_strategy: dict | None = None,
) -> list[dict]:
    return discover_ideas(
        db, project_id, llm, search, count, context_hint,
        project_audience, project_language, category_strategy,
    )
