from __future__ import annotations

import logging
import re

from app.schemas.seo_workflow import IntentAnalysis, asdict

logger = logging.getLogger(__name__)

RECOMMENDED_FORMATS = ("simple_question", "how_to", "comparison", "explainer", "list")

# Correspondance format recommandé -> article_type historique (lu par la FAQ,
# le rapport et le repli de plan).
_FORMAT_TO_ARTICLE_TYPE = {
    "simple_question": "simple_question",
    "how_to": "guide",
    "comparison": "comparison",
    "explainer": "evergreen_information",
    "list": "evergreen_information",
}
_ARTICLE_TYPE_TO_FORMAT = {
    "simple_question": "simple_question",
    "guide": "how_to",
    "comparison": "comparison",
    "transactional": "comparison",
    "navigational": "simple_question",
    "evergreen_information": "explainer",
}

_INTENT_MARKERS = {
    "commercial": (
        "meilleur", "meilleurs", "meilleure", "meilleures", "comparer", "comparatif",
        "comparaison", "vs", "versus", "différence", "choisir", "avis", "alternative",
        "alternatives", "best", "compare", "review", "top",
    ),
    "transactional": (
        "acheter", "prix", "tarif", "tarifs", "commander", "abonnement", "télécharger",
        "essai gratuit", "réserver", "buy", "price", "pricing", "download", "free trial",
    ),
    "navigational": (
        "login", "connexion", "se connecter", "site officiel", "sign in", "sign up",
    ),
}
_HOW_TO_MARKERS = ("comment", "étapes", "tutoriel", "how to", "tutorial", "guide")
_QUESTION_MARKERS = (
    "quoi", "qu'est-ce", "pourquoi", "quand", "quel", "quelle", "quels", "quelles",
    "combien", "faut-il", "est-ce", "what", "why", "when", "which", "is", "can", "does",
)


FIRST_BLOCK_GOALS = {
    "simple_question": "Répondre directement à la question dès les premières phrases.",
    "how_to": "Donner tout de suite la marche à suivre résumée.",
    "comparison": "Donner tout de suite la recommandation selon le profil du lecteur.",
    "explainer": "Expliquer l'essentiel en deux ou trois phrases dès le début.",
    "list": "Annoncer tout de suite ce que la liste apporte et à qui.",
}


def _has_word(text: str, marker: str) -> bool:
    """Correspondance sur mot entier : « free » ne doit pas matcher « freelance »."""
    return re.search(rf"(?<![\w'-]){re.escape(marker)}(?![\w-])", text) is not None


def _count_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for m in markers if _has_word(text, m))


def format_to_article_type(recommended_format: str) -> str:
    return _FORMAT_TO_ARTICLE_TYPE.get(recommended_format, "evergreen_information")


def article_type_to_format(article_type: str) -> str:
    return _ARTICLE_TYPE_TO_FORMAT.get(article_type, "explainer")


def analyze_intent(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> IntentAnalysis:
    """Repli non-LLM, volontairement minimal : il classe le format à partir de
    marqueurs lexicaux (mots entiers) et ne fabrique AUCUNE sous-question ni
    réponse attendue génériques. Le vrai brief d'intention vient de l'étape
    LLM refine_intent_with_research."""
    title_lower = (title or "").lower()
    keyword_lower = (keyword or "").lower()
    head = f"{title_lower} {keyword_lower}"
    text = " ".join([head, (context_hint or "").lower(), (category_name or "").lower()])

    scores = {dim: round(min(1.0, _count_hits(text, markers) / 4.0), 2)
              for dim, markers in _INTENT_MARKERS.items()}
    how_to_hits = _count_hits(head, _HOW_TO_MARKERS)
    question_hits = _count_hits(head, _QUESTION_MARKERS) or (1 if "?" in title_lower else 0)
    scores["informational"] = round(min(1.0, (how_to_hits + question_hits) / 4.0), 2)

    explicit_intent = "informational"
    if scores["navigational"] >= 0.25:
        explicit_intent = "navigational"
    elif scores["transactional"] >= 0.25:
        explicit_intent = "transactional"
    elif scores["commercial"] >= 0.25:
        explicit_intent = "commercial"

    if re.match(r"^\s*\d+\s", title_lower):
        recommended_format = "list"
    elif explicit_intent == "commercial":
        recommended_format = "comparison"
    elif how_to_hits:
        recommended_format = "how_to"
    elif question_hits or explicit_intent == "navigational":
        recommended_format = "simple_question"
    else:
        recommended_format = "explainer"

    analysis = IntentAnalysis(
        explicit_intent=explicit_intent,
        reader_real_question=title or keyword,
        expected_answer="",
        first_block_goal=FIRST_BLOCK_GOALS[recommended_format],
        article_type=format_to_article_type(recommended_format)
        if explicit_intent != "transactional" else "transactional",
        recommended_format=recommended_format,
    )
    analysis.intent_scores = scores
    analysis.commercial_intent_score = scores["commercial"]
    return analysis


def analyze_intent_dict(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> dict:
    return asdict(analyze_intent(title, keyword, context_hint, category_name, idea_discovery, project_context))


def _clean_list(value, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()][:limit]


def refine_intent_with_research(
    base: dict,
    title: str,
    keyword: str,
    research_brief: dict | None = None,
    db=None,
    project_id: str | None = None,
    idea_discovery: dict | None = None,
) -> dict:
    """Produit le vrai brief d'intention par LLM, appuyé sur la SERP réelle :
    question réelle du lecteur, réponse attendue, points indispensables, pièges
    à éviter et format recommandé. Ce brief pilote l'angle, le plan et le writer.

    Le résultat porte toujours ``intent_refine_status`` (ok | empty |
    no_provider | error) pour que l'orchestrateur rende visible un repli sur
    l'heuristique au lieu de le subir en silence."""
    result = dict(base)
    result["refined_by_llm"] = False
    result["intent_refine_status"] = "no_provider"
    if db is None:
        return result
    try:
        from app.services.agents.agent_router import get_agent_router
        provider = get_agent_router(db=db).get_provider("intent_analysis", project_id=project_id)
    except Exception as exc:
        logger.warning("Intent refine: provider resolution failed: %s", exc)
        provider = None
    if provider is None or provider.is_mock:
        return result

    lines = []
    for source in ((research_brief or {}).get("sources_consulted") or [])[:8]:
        if isinstance(source, dict):
            snippet = (source.get("snippet") or "")[:180]
            lines.append(f"- {source.get('title', '')} : {snippet}")
    serp_context = "\n".join(lines)
    idea = idea_discovery or {}
    idea_angle = idea.get("angle") or ""
    idea_answer = str(idea.get("main_answer_summary") or "").strip()
    idea_questions = [str(q) for q in (idea.get("search_questions") or []) if str(q).strip()][:5]
    # Questions « Autres questions posées » de Google : candidates directes
    # aux sous-questions, plus fiables qu'une invention du modèle.
    paa = [
        str(item.get("question") or "").strip()
        for item in ((research_brief or {}).get("people_also_ask") or [])
        if isinstance(item, dict) and str(item.get("question") or "").strip()
    ][:6]

    prompt = (
        "Tu prépares le brief d'un article. Trouve la vraie question que se pose la personne "
        "qui cherche ce sujet, et ce qu'elle doit lire pour repartir satisfaite.\n\n"
        f"Titre : {title}\nMot-clé : {keyword}\n"
        + (f"Angle prévu : {idea_angle}\n" if idea_angle else "")
        + (f"Réponse principale prévue : {idea_answer[:400]}\n" if idea_answer else "")
        + ("Questions prévues : " + " ; ".join(idea_questions) + "\n" if idea_questions else "")
        + ("Questions posées sur Google : " + " ; ".join(paa) + "\n" if paa else "")
        + (f"\nPages déjà classées sur Google :\n{serp_context}\n" if serp_context else "")
        + "\nRéponds UNIQUEMENT avec ce JSON :\n"
        '{"reader_real_question": "la question précise du lecteur, en une phrase", '
        '"expected_answer": "la réponse attendue, en 2 à 3 phrases concrètes", '
        '"recommended_format": "simple_question | how_to | comparison | explainer | list", '
        '"explicit_intent": "informational | commercial | transactional | navigational", '
        '"must_include": ["point indispensable pour bien répondre"], '
        '"must_avoid": ["hors-sujet ou remplissage à éviter"], '
        '"sub_questions": ["question de suivi que le lecteur se pose vraiment"], '
        '"recommended_angle": "l\'angle de l\'article, en une phrase"}\n'
        "Règles : must_include 3 à 5 éléments, must_avoid 2 à 4, sub_questions 0 à 4 "
        "(reprends en priorité les questions posées sur Google qui servent la question du lecteur). "
        "Pas de chiffres inventés. Rédige les valeurs dans la langue du titre."
    )
    try:
        refined = provider.generate_json(prompt, schema_hint="json intent brief object")
    except Exception as exc:
        logger.warning("Intent refine: LLM call failed: %s", exc)
        result["intent_refine_status"] = "error"
        return result
    if not isinstance(refined, dict) or not (refined.get("reader_real_question") or refined.get("expected_answer")):
        logger.warning("Intent refine: LLM returned an empty or unusable brief for %r", title)
        result["intent_refine_status"] = "empty"
        return result

    for field in ("reader_real_question", "expected_answer", "recommended_angle"):
        value = refined.get(field)
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    intent = str(refined.get("explicit_intent") or "").strip().lower()
    if intent in ("informational", "commercial", "transactional", "navigational"):
        result["explicit_intent"] = intent
    fmt = str(refined.get("recommended_format") or "").strip().lower()
    if fmt in RECOMMENDED_FORMATS:
        result["recommended_format"] = fmt
        result["article_type"] = format_to_article_type(fmt)
        result["first_block_goal"] = FIRST_BLOCK_GOALS[fmt]
    result["must_include"] = _clean_list(refined.get("must_include"), 6)
    result["must_avoid"] = _clean_list(refined.get("must_avoid"), 5)
    result["what_to_avoid"] = list(result["must_avoid"])
    result["sub_questions"] = _clean_list(refined.get("sub_questions"), 5)
    result["refined_by_llm"] = True
    result["intent_refine_status"] = "ok"
    return result
