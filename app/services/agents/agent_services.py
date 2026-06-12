"""LLM-based agent implementations for agents that were heuristic-only or missing.

These services use AgentRouter to obtain the right LLM provider for each agent,
enabling per-agent provider configuration from the CMS.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.agents.agent_router import AgentRouter, get_agent_router
from app.services.agents.agent_registry import get_agent

logger = logging.getLogger(__name__)


def _get_router(db=None) -> AgentRouter:
    return get_agent_router(db=db)


def fact_check_article(
    content: str,
    title: str,
    keyword: str | None = None,
    db=None,
) -> dict[str, Any]:
    """Check factual claims in article content using the fact_checker agent."""
    router = _get_router(db)
    provider = router.get_provider("fact_checker")
    if provider.is_mock:
        return {
            "status": "skipped",
            "message": "Fact checker not configured (mock provider)",
            "fact_checks": [],
            "overall_risk": "unknown",
        }

    prompt = (
        f"Tu es un vérificateur de faits expert. Analyse l'article suivant et identifie "
        f"les affirmations factuelles qui pourraient être inexactes, exagérées ou non étayées.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword or 'N/A'}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"fact_checks": [{"claim": "...", "verdict": "accurate|questionable|inaccurate|unsupported", '
        '"explanation": "...", "confidence": 0.0-1.0}], '
        '"overall_risk": "low|medium|high", "summary": "..."}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json fact_check object")
        if isinstance(result, dict) and "fact_checks" in result:
            return result
        return {"status": "error", "message": "Invalid response format", "fact_checks": [], "overall_risk": "unknown"}
    except Exception as exc:
        logger.warning("Fact checker agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "fact_checks": [], "overall_risk": "unknown"}


def seo_optimize_content(
    content: str,
    title: str,
    keyword: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    db=None,
) -> dict[str, Any]:
    """Optimize content for SEO using the seo_optimizer agent."""
    router = _get_router(db)
    provider = router.get_provider("seo_optimizer")
    if provider.is_mock:
        return {
            "status": "skipped",
            "message": "SEO optimizer not configured (mock provider)",
            "suggestions": [],
            "optimized_content": None,
        }

    prompt = (
        f"Tu es un expert SEO. Analyse et optimise le contenu suivant.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé principal : {keyword or 'N/A'}\n"
        f"Meta title actuel : {meta_title or 'N/A'}\n"
        f"Meta description actuelle : {meta_description or 'N/A'}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"suggestions": [{"type": "title|meta_description|headers|keyword_density|internal_links|structure", '
        '"issue": "...", "recommendation": "...", "priority": "high|medium|low"}], '
        '"optimized_content": null ou le contenu optimisé, '
        '"seo_score_estimate": 0.0-1.0, "summary": "..."}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json seo suggestions")
        if isinstance(result, dict) and "suggestions" in result:
            return result
        return {"status": "error", "message": "Invalid response format", "suggestions": [], "optimized_content": None}
    except Exception as exc:
        logger.warning("SEO optimizer agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "suggestions": [], "optimized_content": None}


def editorial_review(
    content: str,
    title: str,
    keyword: str | None = None,
    db=None,
) -> dict[str, Any]:
    """Review content editorially using the editor_revisor agent."""
    router = _get_router(db)
    provider = router.get_provider("editor_revisor")
    if provider.is_mock:
        return {
            "status": "skipped",
            "message": "Editorial reviewer not configured (mock provider)",
            "revisions": [],
            "overall_quality": "unknown",
        }

    prompt = (
        f"Tu es un relecteur éditorial expert. Révise l'article suivant.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword or 'N/A'}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Évalue : clarté, structure, grammaire, orthographe, style, ton, cohérence.\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"revisions": [{"type": "grammar|style|clarity|structure|tone", '
        '"issue": "...", "suggestion": "...", "severity": "critical|major|minor"}], '
        '"overall_quality": "excellent|good|fair|poor", '
        '"score": 0.0-1.0, "summary": "..."}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json editorial review")
        if isinstance(result, dict) and "revisions" in result:
            return result
        return {"status": "error", "message": "Invalid response format", "revisions": [], "overall_quality": "unknown"}
    except Exception as exc:
        logger.warning("Editorial reviewer agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "revisions": [], "overall_quality": "unknown"}


def quality_rate_article(
    content: str,
    title: str,
    keyword: str | None = None,
    db=None,
) -> dict[str, Any]:
    """Rate article quality using the quality_rater agent."""
    router = _get_router(db)
    provider = router.get_provider("quality_rater")
    if provider.is_mock:
        return {
            "status": "skipped",
            "message": "Quality rater not configured (mock provider)",
            "dimensions": {},
            "overall_score": None,
        }

    prompt = (
        f"Tu es un évaluateur qualité. Évalue l'article suivant sur plusieurs dimensions.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword or 'N/A'}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"dimensions": {'
        '"expertise": 0.0-1.0, "experience": 0.0-1.0, '
        '"authoritativeness": 0.0-1.0, "trustworthiness": 0.0-1.0, '
        '"completeness": 0.0-1.0, "originality": 0.0-1.0, '
        '"readability": 0.0-1.0, "engagement": 0.0-1.0'
        '}, '
        '"overall_score": 0.0-1.0, '
        '"strengths": ["..."], "weaknesses": ["..."], '
        '"summary": "..."}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json quality rating")
        if isinstance(result, dict) and "dimensions" in result:
            return result
        return {"status": "error", "message": "Invalid response format", "dimensions": {}, "overall_score": None}
    except Exception as exc:
        logger.warning("Quality rater agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "dimensions": {}, "overall_score": None}
