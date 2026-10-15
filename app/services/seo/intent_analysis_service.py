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

    first_block_goals = {
        "simple_question": "Répondre directement à la question dès les premières phrases.",
        "how_to": "Donner tout de suite la marche à suivre résumée.",
        "comparison": "Donner tout de suite la recommandation selon le profil du lecteur.",
        "explainer": "Expliquer l'essentiel en deux ou trois phrases dès le début.",
        "list": "Annoncer tout de suite ce que la liste apporte et à qui.",
    }

    analysis = IntentAnalysis(
        explicit_intent=explicit_intent,
        reader_real_question=title or keyword,
        expected_answer="",
        first_block_goal=first_block_goals[recommended_format],
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


def refine_intent_with_research(
    base: dict,
    title: str,
    keyword: str,
    research_brief: dict | None = None,
    db=None,
    project_id: str | None = None,
) -> dict:
    """Affine l'analyse d'intention heuristique avec un jugement LLM appuyé sur
    les VRAIS résultats SERP du research brief (titres + snippets concurrents).
    Point 9 du pipeline : l'heuristique seule inférait l'intention depuis des
    marqueurs lexicaux du titre ; elle ignore ce que la SERP montre réellement
    (type de pages classées, questions posées par les concurrents). Repli
    systématique sur l'analyse de base si aucun provider n'est disponible —
    jamais bloquant, toujours un enrichissement."""
    result = dict(base)
    if db is None:
        return result
    try:
        from app.services.agents.agent_router import get_router
    except Exception:
        return result
    router = get_router(db)
    if router is None:
        return result
    try:
        provider = router.get_provider("intent_analysis", project_id=project_id)
        if provider is None or provider.is_mock:
            return result
    except Exception:
        return result

    sources = (research_brief or {}).get("sources_consulted") or []
    serp_context = ""
    if sources:
        lines = []
        for source in sources[:10]:
            if isinstance(source, dict):
                snippet = (source.get("snippet") or "")[:200]
                lines.append(f"- {source.get('title', '')} — {snippet}")
        serp_context = "\n".join(lines)

    prompt = (
        "Analyse l'intention de recherche réelle derrière ce sujet d'article en t'appuyant sur "
        "les résultats Google réels (SERP) ci-dessous. Détermine : explicit_intent (informational|"
        "commercial|transactional|navigational), article_type (evergreen_information|guide|"
        "comparison|transactional|navigational|simple_question), la vraie question du lecteur, "
        "la réponse attendue, les sous-questions à traiter, l'angle recommandé et ce qu'il faut "
        "éviter (ce que les concurrents ratent).\n\n"
        f"Titre : {title}\nMot-clé : {keyword}\n\n"
        + (f"Résultats SERP réels :\n{serp_context}\n\n" if serp_context else "Aucun résultat SERP disponible.\n\n")
        + "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"explicit_intent": "...", "article_type": "...", "reader_real_question": "...", '
        '"expected_answer": "...", "sub_questions": ["...", "..."], "first_block_goal": "...", '
        '"recommended_angle": "...", "what_to_avoid": ["...", "..."]}'
    )
    try:
        refined = provider.generate_json(prompt, schema_hint="json intent analysis object")
    except Exception:
        return result
    if not isinstance(refined, dict):
        return result

    for field in ("explicit_intent", "article_type", "reader_real_question", "expected_answer",
                  "first_block_goal", "recommended_angle"):
        value = refined.get(field)
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    for list_field in ("sub_questions", "what_to_avoid"):
        value = refined.get(list_field)
        if isinstance(value, list) and value:
            result[list_field] = [str(x) for x in value if str(x).strip()][:8]
    result["refined_by_llm"] = True
    if isinstance(result.get("intent_scores"), dict):
        result["intent_scores"] = dict(result["intent_scores"])
    return result
