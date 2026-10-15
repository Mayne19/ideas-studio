from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import Article, ArticleKeyword, Category, Keyword
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import IdeaDiscoveryResult, asdict
from app.services.providers.llm_provider import LLMProvider
from app.services.providers.search_provider import SearchProvider, MockSearchProvider
from app.services.seo.adapters.serp_adapter import serp_adapter
from app.services.seo.adapters.trends_adapter import trends_adapter

_EXISTING_KEYWORD_STATUSES = (
    ArticleStatus.PUBLISHED,
    ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.IDEA_PROPOSED,
    ArticleStatus.IDEA_PRIORITY,
)


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
    categories = db.execute(select(Category).where(Category.project_id == project_id)).scalars().all()
    category_id = None
    if category_strategy and category_strategy.get("chosen_category_id"):
        category_id = category_strategy["chosen_category_id"]

    existing_keywords = {
        term for term, in db.execute(
            select(Keyword.term)
            .join(ArticleKeyword, ArticleKeyword.keyword_id == Keyword.id)
            .join(Article, Article.id == ArticleKeyword.article_id)
            .where(
                Article.project_id == project_id,
                Article.status_reason_id.in_(_EXISTING_KEYWORD_STATUSES),
            )
        ).all()
    }

    # Matière humaine réelle (Reddit, People Also Ask, Google Autocomplete,
    # StackOverflow, Quora, YouTube, Twitter/Nitter) — jusqu'ici cette
    # extraction n'était appelée qu'à la rédaction de l'article
    # (seo_generation_orchestrator.py), après que le sujet soit déjà choisi
    # par le LLM sans aucune donnée réelle sur ce que les internautes
    # cherchent vraiment. Récupérée une seule fois pour tout le lot (même
    # sujet source), pas par idée. Le mot-clé de recherche est context_hint
    # s'il existe, sinon la catégorie choisie par la stratégie — jamais une
    # recherche sans sujet, qui ne renverrait rien d'exploitable.
    human_insights: dict | None = None
    insights_topic = context_hint or (category_strategy or {}).get("chosen_category_name")
    if insights_topic and not llm.is_mock:
        try:
            from app.services.seo.human_insights_service import extract_human_insights
            human_insights = extract_human_insights(
                keyword=insights_topic, project_id=project_id, language=project_language,
            )
        except Exception:
            human_insights = None

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

                trend_hint = ""
                if trends_adapter.configured and context_hint:
                    trend = trends_adapter.get_trends(context_hint)
                    if trend.get("status") == "success" and trend.get("trend_score") is not None:
                        direction = "en hausse" if trend["trend_score"] > 1.2 else "stable ou en baisse" if trend["trend_score"] < 0.8 else "stable"
                        trend_hint = f"Tendance estimée sur ce sujet : {direction} (proxy, pas une mesure officielle).\n"

                # Matière humaine réelle piochée par idée : chaque idée du lot pioche
                # dans une tranche différente des questions/points de friction
                # remontés (Reddit, PAA, Autocomplete, StackOverflow, Quora, YouTube,
                # Twitter) pour éviter que les 5 idées convergent vers le même
                # insight — jamais de contenu inventé si l'extraction a échoué.
                human_insights_hint = ""
                if human_insights and human_insights.get("status") == "completed":
                    questions = human_insights.get("questions", [])
                    pain_points = human_insights.get("pain_points", [])
                    real_examples = human_insights.get("real_examples", [])
                    picked = []
                    if questions:
                        picked.append(f"Vraie question posée par des internautes : \"{questions[i % len(questions)]}\"")
                    if pain_points:
                        picked.append(f"Vraie frustration remontée : \"{pain_points[i % len(pain_points)]}\"")
                    if real_examples:
                        picked.append(f"Exemple réel partagé : \"{real_examples[i % len(real_examples)]}\"")
                    if picked:
                        human_insights_hint = (
                            "Matière humaine réelle disponible sur ce sujet (Reddit, People Also Ask, "
                            "Google Autocomplete, StackOverflow, Quora, YouTube) :\n"
                            + "\n".join(f"- {p}" for p in picked)
                            + "\nBase ton idée sur cette vraie demande.\n"
                        )

                prompt = (
                    f"Propose une idée d'article de blog en langue '{project_language}', qui répond "
                    "à une vraie question que se pose le lecteur.\n"
                    f"Audience : {project_audience or 'grand public'}.\n"
                    f"Sujet : {context_hint or 'aucun'}.\n"
                    f"{trend_hint}"
                    + (f"Résultats Google actuels :\n{serp_context}\n" if serp_context else "")
                    + f"{human_insights_hint}\n"
                    "Le titre formule clairement la question ou le besoin du lecteur, sans "
                    "superlatif ('ultime', 'complet', 'incontournable') ni promesse creuse.\n"
                    "Réponds en JSON : {\"title\": \"...\", \"keyword\": \"...\", "
                    "\"reader_question\": \"la question précise du lecteur\", "
                    "\"angle\": \"ce que l'article apporte, en une phrase\", "
                    "\"search_intent\": \"informational|commercial|transactional\"}"
                )
                idea_data = llm.generate_json(
                    prompt,
                    schema_hint='{"title": "...", "keyword": "...", "reader_question": "...", "angle": "...", "search_intent": "..."}',
                )
                if isinstance(idea_data, dict):
                    title = idea_data.get("title") or title
                    keyword = idea_data.get("keyword") or keyword
                    idea_angle = str(idea_data.get("angle") or "").strip()
                    reader_question = str(idea_data.get("reader_question") or "").strip()
                    intent_value = str(idea_data.get("search_intent") or "").strip().lower()
                    if intent_value in ("informational", "commercial", "transactional", "navigational"):
                        detected_intent = intent_value

            if keyword in existing_keywords:
                continue

            ref = IdeaDiscoveryResult(
                title=title,
                category_id=category_id or (categories[0].id if categories else None),
                main_keyword=keyword,
                secondary_keywords=[keyword],
                detected_intent=detected_intent,
                angle=idea_angle,
                reader_question=reader_question,
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
