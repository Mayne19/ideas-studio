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
                            + "\nBase ton idée sur cette vraie demande plutôt que sur une supposition "
                            "générique — c'est ce que les internautes cherchent réellement en ce moment.\n"
                        )

                # Format de titre imposé au coup par coup (choisi selon l'index pour
                # forcer la variété plutôt que de laisser le LLM retomber sur son
                # patron par défaut "[Sujet] : Le Guide [Superlatif] pour [Cible]",
                # observé systématiquement sans cette contrainte.
                title_formats = [
                    "une question directe que se pose vraiment le lecteur (ex: 'Pourquoi votre site vitrine ne génère aucun client ?')",
                    "une affirmation tranchée ou contre-intuitive (ex: 'Le CMS que la plupart des entrepreneurs choisissent pour les mauvaises raisons')",
                    "un chiffre concret et spécifique (ex: '6 erreurs de copywriting qui font fuir vos visiteurs avant la première phrase')",
                    "un angle qui déconseille une pratique populaire ou révèle une idée reçue fausse",
                    "une situation précise vécue par le lecteur plutôt qu'une cible générique (ex: 'vous avez du trafic mais zéro contact', 'votre site existe depuis 2 ans mais ne convertit pas')",
                ]
                title_format = title_formats[i % len(title_formats)]

                prompt = (
                    f"Génère une idée d'article SEO originale en langue '{project_language}'.\n"
                    f"Audience cible : {project_audience or 'grand public'}.\n"
                    f"Contexte : {context_hint or 'aucun'}.\n"
                    f"{trend_hint}"
                    f"Contexte SERP :\n{serp_context}\n\n"
                    f"{human_insights_hint}"
                    f"Format de titre imposé : {title_format}\n"
                    "Interdits dans le titre : 'Ultime', 'Incontournable', 'Essentiel', 'Complet', "
                    "'Puissant', 'Booster', 'Révolutionnaire', 'Exhaustif', 'Guide complet pour', "
                    "ainsi que toute structure '[Sujet] : Le Guide [Superlatif] pour [Cible]'.\n"
                    "La cible doit être précise, jamais générique : pas 'les entrepreneurs' mais "
                    "'les freelances qui lancent leur premier site', pas 'les PME' mais "
                    "'les e-commerçants avec moins de 100 commandes par mois'. Ne réutilise jamais "
                    "la même formule de cible ('pour Entrepreneurs et Freelances', 'pour PME et "
                    "Indépendants').\n"
                    "L'idée ne doit pas se contenter de couvrir un sujet : elle doit contredire une "
                    "idée reçue, révéler quelque chose que les articles concurrents n'osent pas dire, "
                    "ou partir d'une situation concrète vécue par un lecteur francophone réel.\n\n"
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
