"""
Couche LLM optionnelle pour l'expert EEAT v2.1.

Appelée uniquement si LLMBudgetManager.should_call_llm() retourne True.
Retourne un score LLM 0-100 qui enrichit le score rules à 85% + LLM à 15%.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.services.seo.helpers import strip_html

EEAT_LLM_SYSTEM = (
    "Tu es un éditeur senior spécialisé en SEO. "
    "Évalue uniquement l'expertise démontrée dans l'article. "
    "Réponds UNIQUEMENT en JSON valide, sans texte autour."
)

EEAT_LLM_PROMPT_TEMPLATE = """Évalue cet article. Format déclaré : {content_format}.

Retourne ce JSON exact :
{{
  "demonstrates_expertise": true,
  "adds_unique_value": true,
  "trustworthy_tone": true,
  "expertise_score": 72,
  "main_weakness": "courte description en max 100 caractères"
}}

Article (3000 premiers caractères) :
{content_excerpt}"""


def _truncate(text: str, max_chars: int = 3000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def call_eeat_llm(article: Any, content_format: str) -> dict | None:
    """
    Call the configured LLM provider to enrich EEAT evaluation.
    Returns a dict with 'score' and 'signals', or None on failure.
    """
    if isinstance(article, dict):
        content = article.get("content") or ""
    else:
        content = getattr(article, "content", None) or ""

    if not content or len(content.strip()) < 100:
        return None

    text = _truncate(strip_html(content), 3000)
    prompt = EEAT_LLM_PROMPT_TEMPLATE.format(
        content_format=content_format,
        content_excerpt=text,
    )

    try:
        from app.services.providers.llm_provider import get_llm_provider, ProviderUnavailableError
        llm = get_llm_provider()
        if llm.is_mock:
            return None
        raw = llm.generate_json(prompt, schema_hint=EEAT_LLM_SYSTEM)
        if not raw or not isinstance(raw, dict):
            return None
    except Exception:
        return None

    expertise_score = raw.get("expertise_score")
    if expertise_score is None:
        return None
    try:
        score = max(0, min(100, float(expertise_score)))
    except (TypeError, ValueError):
        return None

    signals = {
        "demonstrates_expertise": bool(raw.get("demonstrates_expertise", False)),
        "adds_unique_value": bool(raw.get("adds_unique_value", False)),
        "trustworthy_tone": bool(raw.get("trustworthy_tone", False)),
        "main_weakness": str(raw.get("main_weakness", ""))[:120],
    }

    return {
        "score": round(score),
        "signals": signals,
        "method": "llm",
    }


def blend_eeat_with_llm(rules_score: float, llm_result: dict | None) -> tuple[float, str]:
    """
    Blend rules score (85%) with LLM score (15%).
    Returns (blended_score, method).
    """
    if llm_result is None or "score" not in llm_result:
        return rules_score, "rules"
    blended = round(rules_score * 0.85 + llm_result["score"] * 0.15)
    return float(blended), "rules+llm"
