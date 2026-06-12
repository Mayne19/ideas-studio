import json
import uuid
from datetime import datetime, timezone
from time import perf_counter
from sqlalchemy.orm import Session
from sqlalchemy import select

from typing import Any
from app.models.article import Article
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.providers.search_provider import SearchProvider
from app.services.log_service import log_step


_MOCK_IDEA_TEMPLATES = [
    {
        "title": "Comment optimiser votre stratégie de contenu SEO en {year}",
        "keyword": "stratégie contenu SEO",
        "angle": "Guide pratique avec étapes concrètes",
        "search_intent": "informational",
        "audience": "Marketeurs et blogueurs débutants",
        "main_answer_summary": "Une stratégie de contenu SEO repose sur 5 piliers : recherche de mots-clés, analyse d'intention, production de contenu, optimisation technique et mesure des performances.",
        "opportunity_justification": "Fort potentiel car sujet lié à une catégorie prioritaire et manque de contenu existant.",
        "recommended_format": "guide",
        "target_word_count": 2500,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "moyenne",
        "secondary_keywords": ["content marketing", "SEO stratégique", "calendrier éditorial"],
    },
    {
        "title": "Les meilleures pratiques pour accélérer votre site web",
        "keyword": "optimisation vitesse site web",
        "angle": "Checklist technique actionnable",
        "search_intent": "informational",
        "audience": "Développeurs web",
        "main_answer_summary": "Les 7 optimisations clés : mise en cache, compression des images, minification CSS/JS, chargement différé, CDN, optimisation du temps de réponse serveur et réduction des requêtes HTTP.",
        "opportunity_justification": "Sujet toujours recherché avec fort volume et concurrence modérée.",
        "recommended_format": "list",
        "target_word_count": 2000,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "moyenne",
        "secondary_keywords": ["Core Web Vitals", "Lighthouse", "PageSpeed Insights"],
    },
    {
        "title": "Guide complet : créer un blog rentable en partant de zéro",
        "keyword": "créer blog rentable",
        "angle": "Étapes détaillées du débutant à l'expert",
        "search_intent": "informational",
        "audience": "Entrepreneurs en ligne",
        "main_answer_summary": "Un blog rentable nécessite : une niche bien choisie, du contenu régulier de qualité, une stratégie SEO solide, des sources de monétisation diversifiées et une audience engagée.",
        "opportunity_justification": "Sujet intemporel avec fort potentiel de conversion.",
        "recommended_format": "guide",
        "target_word_count": 3000,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "faible",
        "secondary_keywords": ["monétisation blog", "choisir niche blog", "SEO débutant"],
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
        "main_answer_summary": tpl["main_answer_summary"],
        "opportunity_justification": tpl["opportunity_justification"],
        "recommended_format": tpl["recommended_format"],
        "target_word_count": tpl["target_word_count"],
        "needs_faq": tpl["needs_faq"],
        "needs_images": tpl["needs_images"],
        "estimated_difficulty": tpl["estimated_difficulty"],
        "secondary_keywords": tpl["secondary_keywords"],
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
    keyword: str | None = None,
    category_id: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
    search_intent: str | None = None,
    agent_router: Any | None = None,
) -> Article | None:
    started_at = perf_counter()

    if agent_router is not None:
        try:
            llm = agent_router.get_provider("idea_generator")
        except Exception:
            pass
    log_step(
        db,
        project_id,
        f"Génération d'idée lancée avec LLM={llm.describe()} et search={search.describe()}",
        level="info",
        step="generate_idea",
    )
    if llm.is_mock:
        log_step(
            db,
            project_id,
            "Mode mock actif pour la génération d'idée. Résultat non destiné à la production.",
            level="warning",
            step="generate_idea",
        )
        idea_data = _next_mock_idea(audience or project_audience)
    else:
        query = keyword or context_hint or f"idées d'articles SEO pour {audience or project_audience or 'un blog'} en {project_language}"
        search_results = search.search(query, limit=5)
        serp_snippets = "\n".join(f"- {r.title}: {r.snippet}" for r in search_results)

        schema_hint = '{"title": "...", "keyword": "...", "angle": "...", "search_intent": "informational|commercial|transactional|navigational", "audience": "...", "main_answer_summary": "...", "opportunity_justification": "...", "recommended_format": "guide|list|comparatif|tutoriel|analyse|definition", "target_word_count": 2000, "needs_faq": true, "needs_images": true, "estimated_difficulty": "faible|moyenne|forte", "secondary_keywords": ["kw1", "kw2"]}'
        prompt = (
            f"Génère une idée d'article SEO originale pour un blog en langue '{project_language}'.\n"
            f"Audience cible : {audience or project_audience or 'grand public'}.\n"
            f"Titre souhaité : {preferred_title or 'à proposer librement'}.\n"
            f"Mot-clé prioritaire : {keyword or 'à déduire du contexte'}.\n"
            f"Angle éditorial souhaité : {angle or 'à proposer librement'}.\n"
            f"Intention de recherche souhaitée : {search_intent or 'à estimer'}.\n"
            f"Contexte utilisateur : {context_hint or 'aucun contexte additionnel'}.\n"
            f"Contexte SERP actuel :\n{serp_snippets}\n\n"
            f"L'idée doit inclure un pré-brief complet : résumé de la réponse principale, justification du score d'opportunité, format recommandé, longueur cible, besoin FAQ/images, difficulté estimée et mots-clés secondaires.\n"
            f"Réponds uniquement en JSON."
        )
        idea_data = llm.generate_json(prompt, schema_hint=schema_hint)
        if not isinstance(idea_data, dict) or not idea_data:
            raise GenerationFailedError("La génération IA n'a pas produit de proposition d'idée exploitable.")
        if not idea_data.get("keyword") and not keyword:
            log_step(db, project_id, "LLM n'a pas retourné de keyword valide", level="warning", step="generate_idea")
            return None

        idea_data["opportunity_score"] = min(1.0, len(search_results) / 10.0 + 0.3)
        idea_data["serp_summary"] = {"top_results": [{"title": r.title, "url": r.url} for r in search_results]}

    final_keyword = (keyword or idea_data.get("keyword", "")).strip()
    if not final_keyword:
        return None

    if _keyword_already_active(db, project_id, final_keyword):
        log_step(db, project_id, f"Idée ignorée (keyword déjà actif) : {final_keyword}", level="info", step="generate_idea")
        return None

    generated_title = idea_data.get("title", final_keyword)
    final_title = preferred_title or generated_title
    final_audience = audience or idea_data.get("audience") or project_audience
    final_angle = angle or idea_data.get("angle")
    final_search_intent = search_intent or idea_data.get("search_intent")

    article = Article(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category_id=category_id,
        title=final_title,
        slug=f"idea-{uuid.uuid4().hex[:8]}",
        keyword=final_keyword,
        angle=final_angle,
        search_intent=final_search_intent,
        audience=final_audience,
        opportunity_score=idea_data.get("opportunity_score", 0.5),
        serp_summary_json=json.dumps(idea_data.get("serp_summary", {})),
        status="idea_proposed",
        priority=0,
        word_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        # Pre-brief fields
        main_answer_summary=idea_data.get("main_answer_summary"),
        opportunity_justification=idea_data.get("opportunity_justification"),
        recommended_format=idea_data.get("recommended_format"),
        target_word_count=idea_data.get("target_word_count"),
        needs_faq=idea_data.get("needs_faq"),
        needs_images=idea_data.get("needs_images"),
        estimated_difficulty=idea_data.get("estimated_difficulty"),
        proposal_source="ia_generation",
        # Secondary keywords stored as secondary_keywords_json
        secondary_keywords_json=json.dumps(idea_data.get("secondary_keywords", [])),
        # Initial workflow tracking
        workflow_run_id=str(uuid.uuid4()),
        workflow_status="planning",
        completed_agent_keys=json.dumps(["idea_generator"]),
        next_agent_key="intent_analyzer",
        planning_brief_json=json.dumps({
            "title": final_title,
            "keyword": final_keyword,
            "angle": final_angle,
            "search_intent": final_search_intent,
            "audience": final_audience,
            "main_answer_summary": idea_data.get("main_answer_summary"),
            "opportunity_score": idea_data.get("opportunity_score", 0.5),
            "opportunity_justification": idea_data.get("opportunity_justification"),
            "recommended_format": idea_data.get("recommended_format"),
            "target_word_count": idea_data.get("target_word_count"),
            "needs_faq": idea_data.get("needs_faq"),
            "needs_images": idea_data.get("needs_images"),
            "estimated_difficulty": idea_data.get("estimated_difficulty"),
            "secondary_keywords": idea_data.get("secondary_keywords", []),
            "proposal_source": "ia_generation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False),
    )
    db.add(article)
    log_step(db, project_id, f"Idée générée : {article.title}", level="info", step="generate_idea", article_id=article.id)
    duration_ms = int((perf_counter() - started_at) * 1000)
    log_step(
        db,
        project_id,
        f"Génération d'idée terminée en {duration_ms} ms via {llm.describe()}",
        level="info",
        step="generate_idea",
        article_id=article.id,
    )
    db.flush()
    return article
