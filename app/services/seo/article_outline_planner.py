from __future__ import annotations

import logging

from app.schemas.seo_workflow import ArticleOutline, asdict

logger = logging.getLogger(__name__)


def build_outline(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    keyword_brief: dict | None = None,
    editorial_angle: dict | None = None,
    article_type: str = "evergreen_information",
    outline_planner_mode: str = "llm",
    db=None,
    project_id: str | None = None,
) -> ArticleOutline:
    if outline_planner_mode == "llm":
        llm_outline = _build_outline_with_llm(
            title, keyword, intent_analysis, research_brief,
            keyword_brief, editorial_angle, article_type, db, project_id,
        )
        if llm_outline is not None:
            return llm_outline
        logger.warning("LLM outline failed — falling back to heuristic outline")
    return _build_outline_heuristic(title, keyword, intent_analysis, article_type)


def _build_outline_with_llm(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    keyword_brief: dict | None = None,
    editorial_angle: dict | None = None,
    article_type: str = "evergreen_information",
    db=None,
    project_id: str | None = None,
) -> ArticleOutline | None:
    """Plan d'article généré par LLM — plus riche que les patrons heuristiques,
    chaque section justifie son existence (purpose) et sa valeur pour le
    lecteur (reader_value). Retourne None en cas d'échec pour permettre le
    repli heuristique."""
    from app.services.agents.agent_router import get_agent_router

    try:
        router = get_agent_router(db=db)
        provider = router.get_provider("outline_planner", project_id=project_id)
    except Exception as exc:
        logger.warning("Outline planner provider resolution failed: %s", exc)
        return None
    if provider.is_mock:
        return None

    intent = intent_analysis or {}
    brief = research_brief or {}
    kb = keyword_brief or {}
    angle = editorial_angle or {}

    prompt = (
        "Tu es un stratège de contenu SEO. Construis le plan (outline) d'un article "
        "de blog en français. Chaque section doit exister pour une vraie raison : "
        "couvrir un sous-sujet que le lecteur cherche, répondre à une vraie question, "
        "lever une objection. Interdis-toi les sections de remplissage.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword}\n"
        f"Type d'article : {article_type}\n"
        f"Intention de recherche : {intent.get('explicit_intent', '')}\n"
        f"Questions secondaires à couvrir : {', '.join(intent.get('sub_questions') or [])}\n"
        f"Questions réelles du lecteur : {', '.join((intent.get('reader_real_question') or '').split('|'))}\n"
        f"Angle éditorial : {angle.get('main_angle', '')}\n"
        f"Promesse éditoriale : {angle.get('editorial_promise', '')}\n"
        f"Douleurs à adresser : {', '.join(brief.get('field_signals') or [])[:400]}\n"
        f"Angles concurrents identifiés : {', '.join(brief.get('competitor_angles') or [])[:400]}\n"
        f"Mots-clés secondaires : {', '.join(kb.get('secondary_keywords') or [])}\n\n"
        "Contraintes :\n"
        "- 5 à 8 sections H2 maximum\n"
        "- Chaque section a un purpose (pourquoi elle existe) et une reader_value "
        "(ce que le lecteur y gagne)\n"
        "- Pas de section 'Conclusion' : l'article se termine dans la dernière section\n"
        "- Si une FAQ est utile, signale faq_planned=true\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"h1": titre, "intro_goal": "...", "first_block_goal": "...", '
        '"sections": [{"heading": "...", "level": 2, "purpose": "...", '
        '"key_points": ["..."], "reader_value": "..."}], '
        '"conclusion_title": "...", "faq_planned": true|false, "callouts_planned": true|false}'
    )

    try:
        result = provider.generate_json(prompt, schema_hint="json article outline object")
    except Exception as exc:
        logger.warning("Outline planner agent failed: %s", exc)
        return None

    if not isinstance(result, dict) or not isinstance(result.get("sections"), list):
        logger.warning("Outline planner returned invalid format")
        return None

    sections = result.get("sections", [])
    normalized = []
    for s in sections:
        if not isinstance(s, dict) or not s.get("heading"):
            continue
        normalized.append({
            "heading": s.get("heading", ""),
            "level": int(s.get("level", 2)),
            "purpose": s.get("purpose", ""),
            "key_points": s.get("key_points") or [],
            "reader_value": s.get("reader_value", ""),
        })
    if not normalized:
        logger.warning("Outline planner returned no usable sections")
        return None

    return ArticleOutline(
        h1=result.get("h1") or title,
        intro_goal=result.get("intro_goal") or "Présenter le sujet et accrocher le lecteur",
        first_block_goal=result.get("first_block_goal") or "",
        sections=normalized,
        conclusion_title=result.get("conclusion_title") or "Ce qu'il faut retenir",
        faq_planned=bool(result.get("faq_planned")),
        callouts_planned=bool(result.get("callouts_planned")),
    )


def _build_outline_heuristic(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    article_type: str = "evergreen_information",
) -> ArticleOutline:
    outline = ArticleOutline(
        h1=title,
        intro_goal="Présenter le sujet et accrocher le lecteur",
        first_block_goal="",
        conclusion_title="Ce qu'il faut retenir",
        faq_planned=False,
        callouts_planned=False,
    )

    intent = intent_analysis or {}
    first_block = intent.get("first_block_goal", "")

    if article_type == "comparison":
        outline.first_block_goal = first_block or "Cadrer les critères de comparaison essentiels"
        outline.sections = [
            {"heading": "Pourquoi comparer ?", "level": 2, "purpose": "Expliquer l'importance de la comparaison", "key_points": ["Contexte", "Enjeux"], "reader_value": "Comprendre l'enjeu"},
            {"heading": "Critères de comparaison", "level": 2, "purpose": "Définir les critères", "key_points": ["Critère 1", "Critère 2", "Critère 3"], "reader_value": "Savoir quoi regarder"},
            {"heading": "Tableau comparatif", "level": 2, "purpose": "Comparer visuellement", "key_points": ["Points communs", "Différences"], "reader_value": "Voir les différences clairement"},
            {"heading": "Comment choisir ?", "level": 2, "purpose": "Aider à la décision", "key_points": ["Cas d'usage"], "reader_value": "Faire le bon choix"},
        ]
    elif article_type == "guide":
        outline.first_block_goal = first_block or "Donner une première action immédiate"
        outline.sections = [
            {"heading": "Qu'est-ce que c'est ?", "level": 2, "purpose": "Définir le concept", "key_points": [], "reader_value": "Comprendre les bases"},
            {"heading": "Étape 1 : Préparation", "level": 2, "purpose": "Première étape pratique", "key_points": [], "reader_value": "Savoir par où commencer"},
            {"heading": "Étape 2 : Exécution", "level": 2, "purpose": "Étape principale", "key_points": [], "reader_value": "Réaliser l'action principale"},
            {"heading": "Conseils et astuces", "level": 2, "purpose": "Bonnes pratiques", "key_points": ["Astuce 1", "Astuce 2"], "reader_value": "Optimiser son travail"},
        ]
    elif article_type == "simple_question":
        outline.first_block_goal = first_block or "Répondre directement à la question"
        outline.sections = [
            {"heading": "Réponse rapide", "level": 2, "purpose": "Donner la réponse directement", "key_points": ["Réponse principale"], "reader_value": "Obtenir la réponse rapidement"},
            {"heading": "Pourquoi ?", "level": 2, "purpose": "Expliquer le contexte", "key_points": ["Raisons"], "reader_value": "Comprendre le pourquoi"},
            {"heading": "Exemples concrets", "level": 2, "purpose": "Illustrer", "key_points": ["Exemple 1", "Exemple 2"], "reader_value": "Voir des cas réels"},
        ]
    else:
        outline.first_block_goal = first_block or "Donner une information utile au lecteur dès le début"
        outline.sections = [
            {"heading": f"Qu'est-ce que {keyword} ?", "level": 2, "purpose": "Définir le sujet", "key_points": [], "reader_value": "Comprendre les bases"},
            {"heading": f"Pourquoi {keyword} est important ?", "level": 2, "purpose": "Montrer l'importance", "key_points": [], "reader_value": "Saisir les enjeux"},
            {"heading": "Comment faire ?", "level": 2, "purpose": "Guide pratique", "key_points": [], "reader_value": "Savoir appliquer"},
            {"heading": "Bonnes pratiques", "level": 2, "purpose": "Conseils supplémentaires", "key_points": [], "reader_value": "Optimiser ses résultats"},
        ]

    return outline


def build_outline_dict(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    keyword_brief: dict | None = None,
    editorial_angle: dict | None = None,
    article_type: str = "evergreen_information",
    outline_planner_mode: str = "llm",
    db=None,
    project_id: str | None = None,
) -> dict:
    return asdict(build_outline(
        title, keyword, intent_analysis, research_brief, keyword_brief,
        editorial_angle, article_type, outline_planner_mode, db, project_id,
    ))
