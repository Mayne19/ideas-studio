"""
Couche LLM optionnelle pour l'expert GEO v2.1.

Appelée uniquement si LLMBudgetManager.should_call_llm() retourne True.
Formule : rules × 0.80 + LLM × 0.20
"""
from __future__ import annotations

from typing import Any

from app.services.seo.helpers import strip_html

GEO_LLM_SYSTEM = (
    "Tu es un expert en GEO (Generative Engine Optimization). "
    "Évalue si cet article est optimisé pour être cité par les moteurs IA (ChatGPT, Perplexity, Gemini). "
    "Réponds UNIQUEMENT en JSON valide, sans texte autour."
)

GEO_LLM_PROMPT_TEMPLATE = """Évalue cet article pour la citation par les LLM. Format déclaré : {content_format}.

Retourne ce JSON exact :
{{
  "answers_questions_directly": true,
  "factually_dense": true,
  "entity_rich": true,
  "citable_score": 68,
  "main_improvement": "courte description en max 120 caractères"
}}

Article (3000 premiers caractères) :
{content_excerpt}"""


def _truncate(text: str, max_chars: int = 3000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def call_geo_llm(article: Any, content_format: str) -> dict | None:
    """
    Call LLM to assess GEO optimization potential.
    Returns dict with 'score' and 'signals', or None on failure.
    """
    if isinstance(article, dict):
        content = article.get("content") or ""
    else:
        content = getattr(article, "content", None) or ""

    if not content or len(content.strip()) < 100:
        return None

    text = _truncate(strip_html(content), 3000)
    prompt = GEO_LLM_PROMPT_TEMPLATE.format(
        content_format=content_format,
        content_excerpt=text,
    )

    try:
        from app.services.providers.llm_provider import get_llm_provider
        llm = get_llm_provider()
        if llm.is_mock:
            return None
        raw = llm.generate_json(prompt, schema_hint=GEO_LLM_SYSTEM)
        if not raw or not isinstance(raw, dict):
            return None
    except Exception:
        return None

    citable_score = raw.get("citable_score")
    if citable_score is None:
        return None
    try:
        score = max(0, min(100, float(citable_score)))
    except (TypeError, ValueError):
        return None

    signals = {
        "answers_questions_directly": bool(raw.get("answers_questions_directly", False)),
        "factually_dense": bool(raw.get("factually_dense", False)),
        "entity_rich": bool(raw.get("entity_rich", False)),
        "main_improvement": str(raw.get("main_improvement", ""))[:140],
    }

    return {
        "score": round(score),
        "signals": signals,
        "method": "llm",
    }


def blend_geo_with_llm(rules_score: float, llm_result: dict | None) -> tuple[float, str]:
    """
    Blend rules score (80%) with LLM score (20%).
    Returns (blended_score, method).
    """
    if llm_result is None or "score" not in llm_result:
        return rules_score, "rules"
    blended = round(rules_score * 0.80 + llm_result["score"] * 0.20)
    return float(blended), "rules+llm"
