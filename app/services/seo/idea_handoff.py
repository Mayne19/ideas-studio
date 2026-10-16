from __future__ import annotations

"""A0 IdeaHandoff (chaîne v2, étape 2) : relit le pré-brief d'une idée.

`idea_engine` écrit un artefact `idea_prebrief` (angle, format, réponse
principale, questions de recherche, mots-clés secondaires) que personne ne
relisait : la génération repartait du titre et du mot-clé seuls. Ce module
est purement déterministe (aucun appel LLM) : il charge le pré-brief et le
fusionne dans l'idée, l'intention et le brief mots-clés.
"""

from typing import Any

# Formats du pré-brief d'idée -> formats d'intention du pipeline.
_PREBRIEF_FORMAT_MAP = {
    "guide": "how_to",
    "tutoriel": "how_to",
    "tutorial": "how_to",
    "how_to": "how_to",
    "list": "list",
    "liste": "list",
    "comparatif": "comparison",
    "comparison": "comparison",
    "guide prix": "price_guide",
    "prix": "price_guide",
    "price_guide": "price_guide",
    "analyse": "explainer",
    "definition": "explainer",
    "définition": "explainer",
    "explainer": "explainer",
    "simple_question": "simple_question",
}

MAX_SUB_QUESTIONS = 6
MAX_SECONDARY_KEYWORDS = 10


def _str_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text.lower() not in {o.lower() for o in out}:
            out.append(text)
    return out[:limit]


def _merge_unique(primary: list[str], extra: list[str], limit: int) -> list[str]:
    seen = {p.strip().lower() for p in primary}
    merged = list(primary)
    for item in extra:
        key = item.strip().lower()
        if key and key not in seen:
            merged.append(item.strip())
            seen.add(key)
    return merged[:limit]


def prebrief_format_to_recommended(fmt: str | None) -> str:
    return _PREBRIEF_FORMAT_MAP.get(str(fmt or "").strip().lower(), "")


def load_idea_prebrief(db, article_id: str | None) -> dict:
    """Pré-brief normalisé de l'idée, ou {} si l'article n'en a pas."""
    if db is None or not article_id:
        return {}
    try:
        from app.services.seo.artifacts import get_latest_artifact
        raw = get_latest_artifact(db, article_id, "idea_prebrief")
    except Exception:
        return {}
    return normalize_prebrief(raw)


def normalize_prebrief(raw: dict | None) -> dict:
    if not isinstance(raw, dict) or not raw:
        return {}
    return {
        "angle": str(raw.get("angle") or "").strip(),
        "recommended_format": prebrief_format_to_recommended(raw.get("recommended_format")),
        "raw_format": str(raw.get("recommended_format") or "").strip(),
        "main_answer_summary": str(raw.get("main_answer_summary") or "").strip(),
        "search_questions": _str_list(raw.get("search_questions"), 8),
        "secondary_keywords": _str_list(raw.get("secondary_keywords"), MAX_SECONDARY_KEYWORDS),
        "audience": str(raw.get("audience") or "").strip(),
        "search_intent": str(raw.get("search_intent") or "").strip(),
    }


def apply_prebrief_to_idea(idea_discovery: dict, prebrief: dict) -> dict:
    """Complète l'idée (angle, mots-clés secondaires) sans écraser une
    valeur fournie explicitement par l'utilisateur."""
    if not prebrief:
        return idea_discovery
    merged = dict(idea_discovery)
    if not merged.get("angle") and prebrief.get("angle"):
        merged["angle"] = prebrief["angle"]
    merged["secondary_keywords"] = _merge_unique(
        _str_list(merged.get("secondary_keywords"), MAX_SECONDARY_KEYWORDS),
        prebrief.get("secondary_keywords") or [], MAX_SECONDARY_KEYWORDS,
    )
    if prebrief.get("main_answer_summary"):
        merged["main_answer_summary"] = prebrief["main_answer_summary"]
    if prebrief.get("search_questions"):
        merged["search_questions"] = prebrief["search_questions"]
    if prebrief.get("recommended_format"):
        merged["recommended_format"] = prebrief["recommended_format"]
    merged["prebrief_used"] = True
    return merged


def apply_prebrief_to_intent(intent: dict, prebrief: dict) -> dict:
    """Fusionne le pré-brief dans l'intention. Le brief LLM affiné garde la
    main (il a vu la SERP) ; le pré-brief comble ses trous : réponse attendue,
    format, angle, et ses questions rejoignent les sous-questions."""
    if not prebrief:
        return intent
    merged = dict(intent)
    refined = bool(merged.get("refined_by_llm"))
    if prebrief.get("main_answer_summary") and not merged.get("expected_answer"):
        merged["expected_answer"] = prebrief["main_answer_summary"]
    if prebrief.get("recommended_format") and not refined:
        from app.services.seo.intent_analysis_service import FIRST_BLOCK_GOALS, format_to_article_type
        fmt = prebrief["recommended_format"]
        merged["recommended_format"] = fmt
        merged["article_type"] = format_to_article_type(fmt)
        merged["first_block_goal"] = FIRST_BLOCK_GOALS.get(fmt, merged.get("first_block_goal", ""))
    if prebrief.get("angle") and not merged.get("recommended_angle"):
        merged["recommended_angle"] = prebrief["angle"]
    merged["sub_questions"] = _merge_unique(
        _str_list(merged.get("sub_questions"), MAX_SUB_QUESTIONS),
        prebrief.get("search_questions") or [], MAX_SUB_QUESTIONS,
    )
    merged["idea_prebrief"] = {
        "angle": prebrief.get("angle", ""),
        "recommended_format": prebrief.get("recommended_format", ""),
        "main_answer_summary": prebrief.get("main_answer_summary", ""),
    }
    return merged


def apply_prebrief_to_keyword_brief(keyword_brief: dict, prebrief: dict) -> dict:
    if not prebrief or not prebrief.get("secondary_keywords"):
        return keyword_brief
    merged = dict(keyword_brief)
    merged["secondary_keywords"] = _merge_unique(
        _str_list(merged.get("secondary_keywords"), MAX_SECONDARY_KEYWORDS),
        prebrief["secondary_keywords"], MAX_SECONDARY_KEYWORDS,
    )
    return merged
