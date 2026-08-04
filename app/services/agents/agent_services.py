"""LLM-based agent implementations for agents that were heuristic-only or missing.

These services use AgentRouter to obtain the right LLM provider for each agent,
enabling per-agent provider configuration from the CMS.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.agents.agent_router import AgentRouter, get_agent_router
from app.services.agents.agent_registry import get_agent, AgentStatus

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_RESULT: dict[str, Any] = {"status": "not_implemented", "result": None}


def _check_not_implemented(agent_id: str) -> dict[str, Any] | None:
    """Return a standard not_implemented response if the agent has no real implementation."""
    agent = get_agent(agent_id)
    if agent and agent.status == AgentStatus.not_implemented:
        return _NOT_IMPLEMENTED_RESULT
    return None


def _get_router(db=None) -> AgentRouter:
    return get_agent_router(db=db)


def fact_check_article(
    content: str,
    title: str,
    keyword: str | None = None,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Check factual claims in article content using the fact_checker agent."""
    router = _get_router(db)
    provider = router.get_provider("fact_checker", project_id=project_id)
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


def adapt_editorial_style(
    base_tone: str | None,
    base_reader_level: str | None,
    base_writing_style: str | None,
    title: str,
    keyword: str,
    angle: str | None = None,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Adapte le ton/niveau/style de base du projet au sujet précis de cet
    article — jamais un remplacement, seulement un ajustement dans le même
    esprit (un style "professionnel informationnel" reste professionnel et
    informationnel, mais le niveau de détail/vocabulaire s'ajuste au sujet).
    Repli sur les valeurs de base si aucun provider LLM n'est disponible :
    contrairement au fact-checker, cet agent n'est jamais bloquant."""
    base = {"tone": base_tone, "reader_level": base_reader_level, "writing_style": base_writing_style}
    if not any(base.values()):
        return {"status": "skipped", "message": "Aucun style de base défini sur le projet.", **base}

    router = _get_router(db)
    try:
        provider = router.get_provider("style_guide_builder", project_id=project_id)
    except Exception as exc:
        logger.warning("Style adapter provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", **base}
    if provider.is_mock:
        return {"status": "skipped", "message": "Style adapter not configured (mock provider)", **base}

    prompt = (
        "Tu ajustes une consigne éditoriale de base au sujet précis d'un article, sans jamais "
        "la trahir ni en changer l'esprit — seulement adapter le niveau de détail et le vocabulaire "
        "quand le sujet l'exige (ex: un sujet technique dans un style 'accessible' reste accessible "
        "mais peut nécessiter d'introduire un terme technique avec une explication courte).\n\n"
        f"Style de base du projet :\n"
        f"- Ton : {base_tone or 'non défini'}\n"
        f"- Niveau du lecteur : {base_reader_level or 'non défini'}\n"
        f"- Style d'écriture : {base_writing_style or 'non défini'}\n\n"
        f"Article à rédiger :\n"
        f"- Titre : {title}\n"
        f"- Mot-clé : {keyword}\n"
        f"- Angle éditorial : {angle or 'non précisé'}\n\n"
        "Si le style de base convient déjà parfaitement à ce sujet, renvoie-le tel quel. "
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"tone": "...", "reader_level": "...", "writing_style": "...", '
        '"adapted": true|false, "reasoning": "courte explication si adapted=true, sinon vide"}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json style adaptation object")
        if isinstance(result, dict) and result.get("tone") and result.get("reader_level") and result.get("writing_style"):
            return {"status": "success", **result}
        return {"status": "error", "message": "Invalid response format", **base}
    except Exception as exc:
        logger.warning("Style adapter agent failed: %s", exc)
        return {"status": "error", "message": str(exc), **base}


def seo_optimize_content(
    content: str,
    title: str,
    keyword: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Optimize content for SEO using the seo_optimizer agent."""
    router = _get_router(db)
    provider = router.get_provider("seo_optimizer", project_id=project_id)
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
    project_id: str | None = None,
) -> dict[str, Any]:
    """Review content editorially using the editor agent."""
    router = _get_router(db)
    provider = router.get_provider("editor", project_id=project_id)
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
    project_id: str | None = None,
) -> dict[str, Any]:
    """Rate article quality using the quality_gate agent."""
    router = _get_router(db)
    provider = router.get_provider("quality_gate", project_id=project_id)
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
