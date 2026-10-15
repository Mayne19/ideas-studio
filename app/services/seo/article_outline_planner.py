from __future__ import annotations

import logging
import re

from app.schemas.seo_workflow import ArticleOutline, asdict

logger = logging.getLogger(__name__)

# Nombre de sections H2 selon le format recommandé par le brief d'intention :
# une question simple n'a pas besoin de 8 sections, une liste peut en avoir 9.
SECTION_RANGE_BY_FORMAT = {
    "simple_question": (2, 4),
    "how_to": (4, 7),
    "explainer": (4, 6),
    "comparison": (4, 6),
    "list": (5, 9),
}


def _resolve_format(intent: dict, article_type: str) -> str:
    from app.services.seo.intent_analysis_service import article_type_to_format
    fmt = (intent.get("recommended_format") or "").strip()
    return fmt if fmt in SECTION_RANGE_BY_FORMAT else article_type_to_format(article_type)


def resolve_outline_format(intent: dict | None, article_type: str | None) -> str:
    """Format effectif du plan (le même que celui utilisé par le planner)."""
    return _resolve_format(intent or {}, article_type or "evergreen_information")


# Formats où une numérotation des titres a du sens (étapes, éléments d'une liste).
NUMBERED_HEADING_FORMATS = ("list", "how_to")

# « 1. », « 2) », « 3 - », « Étape 1 : », « Partie 2. », « IV. »… en tête de titre.
_HEADING_ENUM_RE = re.compile(
    r"^\s*(?:(?:[ée]tape|partie|section|point)\s+\d+\s*[:.)\-–]?\s*"
    r"|\d{1,2}\s*[.)\-–:]\s+"
    r"|[IVX]{1,4}\s*[.)\-–]\s+)",
    re.IGNORECASE,
)


def strip_heading_enumeration(heading: str, fmt: str | None = None) -> str:
    """Retire une numérotation en tête de titre (« 1. Webflow ou WordPress »)
    que le planner ajoute même hors format liste. Conservée pour les formats
    liste et tutoriel par étapes."""
    heading = (heading or "").strip()
    if fmt in NUMBERED_HEADING_FORMATS:
        return heading
    stripped = _HEADING_ENUM_RE.sub("", heading, count=1).strip()
    if not stripped:
        return heading
    return stripped[0].upper() + stripped[1:]


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
    fmt = _resolve_format(intent, article_type)
    min_sections, max_sections = SECTION_RANGE_BY_FORMAT[fmt]
    question = intent.get("reader_real_question") or title

    def _join(values, limit=400):
        return "; ".join(str(v) for v in (values or []) if str(v).strip())[:limit]

    context_lines = [
        f"Titre : {title}",
        f"Mot-clé : {keyword}",
        f"Question réelle du lecteur : {question}",
        f"Réponse attendue : {intent.get('expected_answer', '')}",
        f"Format : {fmt}",
        f"Angle : {angle.get('main_angle', '')}",
        f"À inclure : {_join(intent.get('must_include'))}",
        f"À éviter : {_join(intent.get('must_avoid') or intent.get('what_to_avoid'))}",
        f"Questions de suivi : {_join(intent.get('sub_questions'))}",
        f"Angles des concurrents : {_join(brief.get('competitor_angles'))}",
        f"Mots-clés secondaires : {_join(kb.get('secondary_keywords'), 200)}",
    ]
    prompt = (
        "Construis le plan d'un article de blog qui répond précisément à la question du lecteur.\n\n"
        + "\n".join(line for line in context_lines if not line.endswith(": "))
        + "\n\nRègles :\n"
        f"- {min_sections} à {max_sections} sections H2 : le sujet décide, pas de remplissage.\n"
        "- La première section répond directement à la question réelle du lecteur.\n"
        "- Chaque section suivante traite un point dont le lecteur a vraiment besoin ; "
        "rien de ce qui figure dans « À éviter ».\n"
        "- Pas de section définition générique, « pourquoi c'est important » ou « conclusion ».\n"
        "- Titres H2 concrets et variés, différents des titres concurrents.\n"
        "- Une section longue peut avoir des sous-sections H3 (level=3).\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"h1": "...", "intro_goal": "...", "first_block_goal": "...", '
        '"sections": [{"heading": "...", "level": 2, "purpose": "...", '
        '"key_points": ["..."], "reader_value": "..."}], '
        '"faq_planned": true|false, "callouts_planned": true|false}'
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
            "heading": strip_heading_enumeration(str(s.get("heading", "")), fmt),
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
        intro_goal=result.get("intro_goal") or "Répondre à la question du lecteur dès les premières phrases",
        first_block_goal=result.get("first_block_goal") or intent.get("first_block_goal") or "",
        sections=normalized,
        conclusion_title=result.get("conclusion_title") or "",
        faq_planned=bool(result.get("faq_planned")),
        callouts_planned=bool(result.get("callouts_planned")),
    )


def _build_outline_heuristic(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    article_type: str = "evergreen_information",
) -> ArticleOutline:
    """Repli minimal construit sur le brief d'intention : une première section
    qui répond à la question, puis les questions de suivi et points
    indispensables. Aucun intitulé gabarit du type « Qu'est-ce que X ? »."""
    intent = intent_analysis or {}
    fmt = _resolve_format(intent, article_type)
    _, max_sections = SECTION_RANGE_BY_FORMAT[fmt]
    question = (intent.get("reader_real_question") or title or keyword).strip()
    expected = (intent.get("expected_answer") or "").strip()

    sections = [{
        "heading": question,
        "level": 2,
        "purpose": "Répondre directement à la question du lecteur",
        "key_points": [expected] if expected else [],
        "reader_value": "Obtenir la réponse tout de suite",
    }]
    seen = {question.lower()}
    for item in list(intent.get("sub_questions") or []) + list(intent.get("must_include") or []):
        heading = strip_heading_enumeration(str(item), fmt)
        if not heading or heading.lower() in seen or len(sections) >= max_sections:
            continue
        seen.add(heading.lower())
        sections.append({
            "heading": heading, "level": 2, "purpose": "Point dont le lecteur a besoin",
            "key_points": [], "reader_value": "",
        })
    if len(sections) < 2:
        follow_up = {
            "how_to": "Les étapes, dans l'ordre",
            "comparison": "Comment choisir selon votre situation",
            "list": "La liste en détail",
        }.get(fmt, "Les cas particuliers à connaître")
        sections.append({
            "heading": follow_up, "level": 2, "purpose": "Compléter la réponse",
            "key_points": [], "reader_value": "",
        })

    return ArticleOutline(
        h1=title,
        intro_goal="Répondre à la question du lecteur dès les premières phrases",
        first_block_goal=intent.get("first_block_goal") or "Répondre directement à la question",
        sections=sections,
        conclusion_title="",
        faq_planned=False,
        callouts_planned=False,
    )


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
