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


def extract_claims(
    content: str,
    title: str,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Isole les affirmations factuelles vérifiables du contenu (chiffres,
    dates, statistiques, faits attribuables) avant le fact-check complet —
    donne au fact-checker une liste déjà identifiée plutôt que de tout
    redécouvrir depuis zéro sur le texte brut."""
    router = _get_router(db)
    try:
        provider = router.get_provider("claim_extractor", project_id=project_id)
    except Exception as exc:
        logger.warning("Claim extractor provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "claims": []}
    if provider.is_mock:
        return {"status": "skipped", "message": "Claim extractor not configured (mock provider)", "claims": []}

    prompt = (
        "Extrait uniquement les affirmations factuelles vérifiables de cet article : chiffres, "
        "statistiques, dates, faits attribuables à une source, comparaisons quantifiées. "
        "Ignore les opinions, conseils génériques et tournures rhétoriques.\n\n"
        f"Titre : {title}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"claims": [{"text": "affirmation exacte extraite du texte", "type": "statistic|date|fact|comparison", '
        '"verifiable": true|false}]}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json claims object")
        if isinstance(result, dict) and "claims" in result:
            return {"status": "success", **result}
        return {"status": "error", "message": "Invalid response format", "claims": []}
    except Exception as exc:
        logger.warning("Claim extractor agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "claims": []}


def _format_source_for_evidence(source: dict) -> str:
    """Format a source for the evidence pack builder prompt, embedding the
    quality computed by source_quality_service.validate_sources."""
    url = source.get("url", "")
    label = source.get("title") or source.get("snippet") or url
    quality_check = source.get("quality_check") or {}
    if quality_check.get("skipped"):
        quality = "unknown"
    else:
        quality = quality_check.get("quality") or "unknown"
    return f"- {url} : {label} (qualité: {quality})"


def _quality_for_url(url: str, sources: list[dict]) -> str:
    """Look up the quality_check quality computed for a given source URL."""
    for source in sources:
        if source.get("url") == url:
            quality_check = source.get("quality_check") or {}
            if quality_check.get("skipped"):
                return "unknown"
            return quality_check.get("quality") or "unknown"
    return "unknown"


def build_evidence_pack(
    keyword: str,
    title: str,
    research_brief: dict[str, Any],
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Sélectionne, dans les sources déjà collectées par le research brief, les
    faits et sources les plus fiables à utiliser pendant la rédaction — filtre
    et hiérarchise plutôt que de refaire une recherche. Repose entièrement sur
    ce que research_brief a déjà trouvé (aucun nouvel appel réseau)."""
    external_links = research_brief.get("sources_consulted") or []
    if not external_links:
        return {
            "status": "skipped",
            "message": "Aucune source disponible dans le research brief pour constituer un dossier.",
            "evidence_items": [],
        }

    router = _get_router(db)
    try:
        provider = router.get_provider("evidence_pack_builder", project_id=project_id)
    except Exception as exc:
        logger.warning("Evidence pack builder provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "evidence_items": []}
    if provider.is_mock:
        return {"status": "skipped", "message": "Evidence pack builder not configured (mock provider)", "evidence_items": []}

    sources_text = "\n".join(
        _format_source_for_evidence(s) for s in external_links[:12]
    )
    prompt = (
        "À partir de ces sources trouvées pour préparer un article, sélectionne les faits et "
        "données les plus fiables et pertinents à citer, avec leur source d'origine. Chaque source "
        "est annotée avec sa qualité (high/medium/low/unknown : accessibilité et longueur du contenu). "
        "Privilégie systématiquement les sources de qualité 'high', et ignore les sources de qualité "
        "'low' ainsi que les sources hors-sujet. Un fait doit toujours citer une source de qualité "
        "élevée ou moyenne.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword}\n\n"
        f"Sources disponibles :\n{sources_text}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"evidence_items": [{"fact": "...", "source_url": "...", "reliability": "high|medium|low", '
        '"source_quality": "high|medium|low|unknown"}]}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json evidence pack object")
        if isinstance(result, dict) and "evidence_items" in result:
            items = result.get("evidence_items") or []
            for item in items:
                if "source_quality" not in item:
                    item["source_quality"] = _quality_for_url(item.get("source_url", ""), external_links)
            return {"status": "success", **result}
        return {"status": "error", "message": "Invalid response format", "evidence_items": []}
    except Exception as exc:
        logger.warning("Evidence pack builder agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "evidence_items": []}


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
    contrairement au fact-checker, cet agent n'est jamais bloquant.
    Le repli déterministe s'appuie sur 3 templates de style complets
    (accessible, professionnel, technique) avec auto-détection du template
    le plus proche du style de base du projet."""
    base = {"tone": base_tone, "reader_level": base_reader_level, "writing_style": base_writing_style}
    if not any(base.values()):
        return {"status": "skipped", "message": "Aucun style de base défini sur le projet.", **base}

    fallback_guide = build_style_guide_fallback(base_tone, base_reader_level, base_writing_style, title, keyword, angle)

    router = _get_router(db)
    try:
        provider = router.get_provider("style_guide_builder", project_id=project_id)
    except Exception as exc:
        logger.warning("Style adapter provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", **fallback_guide}
    if provider.is_mock:
        return {"status": "skipped", "message": "Style adapter not configured (mock provider)", **fallback_guide}

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
            result["status"] = "success"
            result["style_guide"] = fallback_guide.get("style_guide")
            result["template_used"] = fallback_guide.get("template_used")
            return result
        return {"status": "error", "message": "Invalid response format", **fallback_guide}
    except Exception as exc:
        logger.warning("Style adapter agent failed: %s", exc)
        return {"status": "error", "message": str(exc), **fallback_guide}


STYLE_GUIDE_TEMPLATES: dict[str, dict] = {
    "accessible": {
        "label": "Accessible & conversationnel",
        "rules": [
            "Phrases courtes (10-20 mots), un seul verbe fort par phrase",
            "Vocabulaire courant, chaque terme technique est défini dès sa première occurrence",
            "Tutoiement ou 'vous' chaleureux, jamais de jargon non expliqué",
            "Analogies et exemples concrets tirés de la vie courante",
            "Métaphores visuelles simples pour les concepts abstraits",
            "Intro en 2-3 phrases qui promet un bénéfice concret au lecteur",
        ],
    },
    "professionnel": {
        "label": "Professionnel & informationnel",
        "rules": [
            "Phrases de 15-30 mots, rythme soutenu mais clair",
            "Vocabulaire précis du domaine sans excès de jargon",
            "Structure argumentative : fait, conséquence, recommandation",
            "Chiffres, exemples et cas réels pour crédibiliser chaque affirmation",
            "Ton neutre et confiant, position tranchée argumentée",
            "Transitions logiques implicites, pas de remplissage",
        ],
    },
    "technique": {
        "label": "Technique & expert",
        "rules": [
            "Phrases de 20-35 mots, dense et précise, sans approximation",
            "Terminologie exacte du domaine, définie en note si nécessaire",
            "Détails d'implémentation, benchmarks, données chiffrées sourcées",
            "Hiérarchie claire : concept → mécanisme → application → limites",
            "Aucune généralité : chaque affirmation est étayée",
            "Précision avant lisibilité, mais jamais de phrases impraticables",
        ],
    },
}

_STYLE_TEMPLATE_KEYWORDS = {
    "accessible": [
        "accessible", "conversationnel", "grand public", "simple", "débutant",
        "débutants", "vulgarisé", "vulgarisée", "familier", "grands débutants",
        "pédagogique", "pédagogie",
    ],
    "professionnel": [
        "professionnel", "professionnelle", "informationnel", "informationnelle",
        "business", "entreprise", "corporate", "neutre", "sérieux", "b2b",
        "market", "marketing", "journalistique",
    ],
    "technique": [
        "technique", "expert", "expertise", "avancé", "avancée", "spécialisé",
        "spécialisée", "technicité", "code", "dev", "ingénieur", "scientifique",
        "deep", "geek", "cac40",
    ],
}


def _detect_style_template(base_tone: str | None, base_writing_style: str | None, base_reader_level: str | None) -> str:
    """Auto-détection du template de style le plus proche du style de base."""
    haystack = " ".join(
        w.lower() for w in (base_tone or "", base_writing_style or "", base_reader_level or "") if w
    )
    if not haystack:
        return "professionnel"
    best_template = "professionnel"
    best_score = 0
    for template, keywords in _STYLE_TEMPLATE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in haystack)
        if score > best_score:
            best_score = score
            best_template = template
    return best_template


def build_style_guide_fallback(
    base_tone: str | None,
    base_reader_level: str | None,
    base_writing_style: str | None,
    title: str,
    keyword: str,
    angle: str | None = None,
) -> dict[str, Any]:
    """Repli déterministe : choisit le template de style (3 disponibles) le
    plus proche du style de base du projet et produit un guide de style
    actionnable injectable dans le prompt du writer. Toujours disponible,
    sans dépendance LLM."""
    template = _detect_style_template(base_tone, base_writing_style, base_reader_level)
    guide = STYLE_GUIDE_TEMPLATES[template]
    return {
        "status": "fallback",
        "tone": base_tone or guide["label"],
        "reader_level": base_reader_level or "",
        "writing_style": base_writing_style or guide["label"],
        "template_used": template,
        "style_guide": {
            "label": guide["label"],
            "rules": guide["rules"],
            "subject": {"title": title, "keyword": keyword, "angle": angle},
        },
    }


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


def run_quality_gate(
    content: str,
    title: str,
    keyword: str | None = None,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Juge qualité UNIQUE : un seul appel LLM consolide la revue éditoriale,
    la rétention lecteur, l'engagement et la notation qualité en une seule
    décision (quality_grade). Remplace la multiplication de juges séparés qui
    évaluaient le même texte avec des prompts différents et produisaient des
    avis contradictoires. Repli déterministe si le provider est indisponible."""
    router = _get_router(db)
    provider = router.get_provider("quality_gate", project_id=project_id)
    if provider.is_mock:
        return {
            "status": "skipped",
            "message": "Quality gate not configured (mock provider)",
            "quality_grade": "unknown",
            "decision": "skip",
        }

    prompt = (
        "Tu es le juge qualité unique d'un article de blog. Tu rends UNE seule "
        "décision consolidée en couvrant : structure et clarté, grammaire et style, "
        "accroche et engagement, rétention du lecteur, complétude par rapport au "
        "mot-clé, originalité, et crédibilité éditoriale.\n\n"
        f"Titre : {title}\n"
        f"Mot-clé : {keyword or 'N/A'}\n\n"
        f"Contenu :\n{content[:6000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"quality_grade": "A|B|C|D", '
        '"decision": "pass|minor_fixes|rewrite", '
        '"score": 0.0-1.0, '
        '"strengths": ["..."], "weaknesses": ["..."], '
        '"blocking_issues": ["..."], '
        '"summary": "..."}\n'
        "Grille : A = prêt à publier (≥0.85), B = corrections mineures (0.70-0.84), "
        "C = révision nécessaire (0.55-0.69), D = réécriture (≤0.54)."
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json quality gate object")
        if isinstance(result, dict) and result.get("quality_grade"):
            return {"status": "success", **result}
        return {"status": "error", "message": "Invalid response format", "quality_grade": "unknown", "decision": "rewrite"}
    except Exception as exc:
        logger.warning("Quality gate agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "quality_grade": "unknown", "decision": "rewrite"}


def check_reader_retention(
    content: str,
    title: str,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Détecte les passages où un lecteur risque de décrocher : sections trop
    denses, trop longues sans respiration, jargon non expliqué, absence
    d'exemples concrets sur un point complexe."""
    router = _get_router(db)
    try:
        provider = router.get_provider("reader_retention_checker", project_id=project_id)
    except Exception as exc:
        logger.warning("Reader retention checker provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "drop_off_points": []}
    if provider.is_mock:
        return {"status": "skipped", "message": "Reader retention checker not configured (mock provider)", "drop_off_points": []}

    prompt = (
        "Identifie les passages de cet article où un lecteur risque de décrocher : paragraphes "
        "trop denses ou trop longs sans respiration, jargon non expliqué, sections répétitives, "
        "manque d'exemple concret sur un point complexe.\n\n"
        f"Titre : {title}\n\n"
        f"Contenu :\n{content[:5000]}\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"drop_off_points": [{"excerpt": "extrait concerné", "issue": "...", "suggestion": "..."}], '
        '"retention_score": 0.0-1.0}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json retention object")
        if isinstance(result, dict) and "drop_off_points" in result:
            return {"status": "success", **result}
        return {"status": "error", "message": "Invalid response format", "drop_off_points": []}
    except Exception as exc:
        logger.warning("Reader retention checker agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "drop_off_points": []}


def improve_engagement(
    content: str,
    title: str,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Évalue et améliore l'accroche/engagement en réécrivant par section :
    l'éditeur d'engagement reçoit chaque section (H2 + son contenu) et renvoie
    une version réécrite de cette section avec une meilleure accroche, de
    meilleures transitions et des fins de section qui retiennent l'attention.
    Le contenu hors section (intro, blocs HTML divers) est conservé tel quel.
    Ne retourne jamais de texte partiel : si une section n'est pas réécrite
    correctement, l'original est conservé à la place."""
    router = _get_router(db)
    try:
        provider = router.get_provider("engagement_editor", project_id=project_id)
    except Exception as exc:
        logger.warning("Engagement editor provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "suggestions": [], "rewritten_sections": [], "content": content}
    if provider.is_mock:
        return {"status": "skipped", "message": "Engagement editor not configured (mock provider)", "suggestions": [], "rewritten_sections": [], "content": content}

    import re
    section_pattern = re.compile(r"(<h2[^>]*>.*?</h2>)(.*?)(?=<h2[^>]*>|$)", re.IGNORECASE | re.DOTALL)
    sections = list(section_pattern.finditer(content))
    section_rewrites: dict[int, str] = {}
    rewritten_meta: list[dict] = []

    def _rewrite_section(match: "re.Match") -> str | None:
        prompt = (
            "Améliore l'accroche, les transitions et la fin de CETTE section d'article pour retenir "
            "l'attention du lecteur. Réécris la section en conservant strictement le sens, les faits "
            "et le vocabulaire spécifique. N'invente JAMAIS de chiffres, de citations, d'études ou de "
            "liens. Garde les balises HTML identiques (h3, p, ul, ol, blockquote, table, strong, em). "
            "Rends la section entière (titre H2 + contenu) en HTML valide.\n\n"
            f"Titre de l'article : {title}\n\n"
            f"Section à réécrire :\n{match.group(0)[:4000]}\n\n"
            "Réponds UNIQUEMENT avec un JSON valide :\n"
            '{"rewritten_section": "...HTML complet de la section...", '
            '"improvements": "brève liste des améliorations apportées"}'
        )
        try:
            result = provider.generate_json(prompt, schema_hint="json section rewrite object")
            rewritten = result.get("rewritten_section") if isinstance(result, dict) else None
            if isinstance(rewritten, str) and "<h2" in rewritten and len(rewritten) > len(match.group(0)) * 0.3:
                return rewritten
        except Exception as exc:
            logger.warning("Engagement editor section rewrite failed: %s", exc)
        return None

    if not sections:
        prompt = (
            "Évalue la capacité de cet article à capter et retenir l'attention du lecteur : accroche "
            "d'introduction, transitions entre paragraphes, appels à l'action, questions rhétoriques bien "
            "placées. Rends une version réécrite du contenu avec une meilleure accroche, sans jamais "
            "inventer de chiffres, de citations ou de faits.\n\n"
            f"Titre : {title}\n\n"
            f"Contenu :\n{content[:5000]}\n\n"
            "Réponds UNIQUEMENT avec un JSON valide :\n"
            '{"engagement_score": 0.0-1.0, "rewritten_content": "...HTML complet...", '
            '"hook_quality": "strong|adequate|weak"}'
        )
        try:
            result = provider.generate_json(prompt, schema_hint="json engagement object")
            if isinstance(result, dict) and result.get("rewritten_content"):
                return {
                    "status": "success",
                    "engagement_score": result.get("engagement_score"),
                    "hook_quality": result.get("hook_quality"),
                    "content": result["rewritten_content"],
                    "rewritten_sections": [{"index": 0, "rewritten": True}],
                    "rewritten_count": 1,
                    "suggestions": ["Contenu intégral réécrit pour améliorer l'engagement"],
                }
            return {"status": "error", "message": "Invalid response format", "suggestions": [], "rewritten_sections": [], "content": content}
        except Exception as exc:
            logger.warning("Engagement editor agent failed: %s", exc)
            return {"status": "error", "message": str(exc), "suggestions": [], "rewritten_sections": [], "content": content}

    for index, match in enumerate(sections):
        rewritten = _rewrite_section(match)
        if rewritten:
            section_rewrites[index] = rewritten
        rewritten_meta.append({"index": index, "heading": match.group(1), "rewritten": bool(rewritten)})

    if not section_rewrites:
        return {"status": "error", "message": "No section rewritten", "suggestions": [], "rewritten_sections": rewritten_meta, "content": content}

    parts = []
    last_end = 0
    for i, m in enumerate(sections):
        parts.append(content[last_end:m.start()])
        parts.append(section_rewrites.get(i, m.group(0)))
        last_end = m.end()
    parts.append(content[last_end:])
    new_content = "".join(parts)

    return {
        "status": "success",
        "engagement_score": None,
        "hook_quality": None,
        "content": new_content,
        "rewritten_sections": rewritten_meta,
        "rewritten_count": len(section_rewrites),
        "suggestions": [f"{len(section_rewrites)} section(s) réécrite(s) pour améliorer l'engagement"],
    }


def extract_main_keyword(title: str, db=None, project_id: str | None = None) -> dict[str, Any]:
    """Extrait un mot-clé SEO court (2-5 mots) depuis un titre — utilisé quand
    un article est créé manuellement sans mot-clé explicite. Le repli naïf
    (slugifier le titre entier) pollue tout le pipeline en aval : recherche
    d'images, brief SEO, densité de mot-clé cherchée dans le contenu (observé
    en production : "au-dela-de-lesthetique-comment-le-web-design-impacte..."
    utilisé comme mot-clé au lieu de "web design vitesse SEO")."""
    router = _get_router(db)
    try:
        provider = router.get_provider("keyword_research", project_id=project_id)
    except Exception as exc:
        logger.warning("Keyword extraction provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "keyword": None}
    if provider.is_mock:
        return {"status": "skipped", "message": "Keyword extraction not configured (mock provider)", "keyword": None}

    prompt = (
        f"Titre d'article : {title}\n\n"
        "Extrait le mot-clé SEO principal de ce titre : 2 à 5 mots maximum, "
        "sans ponctuation, celui qu'un internaute taperait réellement dans un moteur de recherche.\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"keyword": "..."}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json keyword object")
        keyword = result.get("keyword") if isinstance(result, dict) else None
        if isinstance(keyword, str) and keyword.strip():
            return {"status": "success", "keyword": keyword.strip()}
        return {"status": "error", "message": "Invalid response format", "keyword": None}
    except Exception as exc:
        logger.warning("Keyword extraction agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "keyword": None}


def plan_section_images(
    section_headings: list[str],
    article_keyword: str,
    db=None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Décide, pour chaque section H2, si une image a du sens et comment la
    trouver — une recherche Unsplash sur un titre de section abstrait
    ("Qu'est-ce que c'est ?", "Comment choisir ?") ou technique
    ("robots.txt", "API REST") renvoie systématiquement des photos sans
    rapport, Unsplash n'ayant aucune photo pour des concepts non visuels.

    Pour chaque section, trois issues possibles :
    - "skip" : sujet trop abstrait/technique, aucune image ne serait pertinente
    - "brand" : la section parle d'un outil/marque identifiable (ex: Canva,
      Figma, Shopify) — chercher une image sur le domaine officiel de cette
      marque plutôt qu'une banque de photos générique
    - "stock" : sujet concret et photographiable (personnes, lieux, objets
      physiques) — une recherche Unsplash classique est pertinente
    """
    router = _get_router(db)
    try:
        provider = router.get_provider("media_planner", project_id=project_id)
    except Exception as exc:
        logger.warning("Image planning provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "sections": []}
    if provider.is_mock:
        return {"status": "skipped", "message": "Image planning not configured (mock provider)", "sections": []}

    headings_list = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(section_headings))
    prompt = (
        f"Mot-clé principal de l'article : {article_keyword}\n\n"
        f"Titres de section (H2) :\n{headings_list}\n\n"
        "Pour CHAQUE section, décide comment illustrer son sujet :\n"
        "- \"skip\" : le sujet est abstrait, structurel ou technique (une question générique, une étape "
        "numérotée, un concept non photographiable comme du code ou un protocole) — aucune image "
        "pertinente n'existe sur une banque de photos.\n"
        "- \"brand\" : la section évoque un outil, un logiciel ou une marque identifiable qui a son "
        "propre site web (ex: Canva, Figma, Shopify, WordPress, Notion) — précise le nom exact de la "
        "marque et son nom de domaine officiel (ex: 'canva.com', jamais un site tiers ou un concurrent).\n"
        "- \"stock\" : le sujet est concret et photographiable (une personne au travail, un objet, un "
        "lieu, une scène réelle) — précise une requête de recherche d'image en anglais, précise et "
        "visuelle (pas juste le titre de section).\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"sections": [{"heading": "...", "decision": "skip|brand|stock", '
        '"brand_name": "..." (si brand), "brand_domain": "..." (si brand), '
        '"stock_query": "..." (si stock)}]}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json image plan object")
        sections = result.get("sections") if isinstance(result, dict) else None
        if isinstance(sections, list):
            return {"status": "success", "sections": sections}
        return {"status": "error", "message": "Invalid response format", "sections": []}
    except Exception as exc:
        logger.warning("Image planning agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "sections": []}


def judge_surprise_moment(content: str, title: str, keyword: str, db=None, project_id: str | None = None) -> dict[str, Any]:
    """Juge si l'article contient au moins une observation, formulation ou
    angle absent des 10 premiers résultats Google sur le même sujet —
    critère "moment de surprise" de la grille de scoring (article_reviewer_
    service.py). Aucune heuristique par mots-clés ne peut vérifier ça
    fiablement (ça demanderait une vraie recherche comparative), un LLM
    avec de bonnes connaissances générales sur le sujet peut au moins
    juger si l'angle est du contenu générique déjà vu partout ou une vraie
    prise de recul. Reste une approximation, pas une recherche réelle
    (contrairement à SerpAdapter qui, lui, interroge un vrai moteur)."""
    router = _get_router(db)
    try:
        provider = router.get_provider("originality_angle_judge", project_id=project_id)
    except Exception as exc:
        logger.warning("Surprise moment judge provider resolution failed: %s", exc)
        return {"status": "skipped", "message": f"Provider indisponible : {exc}", "score": None}
    if provider.is_mock:
        return {"status": "skipped", "message": "Surprise moment judge not configured (mock provider)", "score": None}

    prompt = (
        f"Titre : {title}\nMot-clé : {keyword}\n\n"
        f"Contenu :\n{content[:6000]}\n\n"
        "Sur la base de tes connaissances générales sur ce sujet, cet article contient-il au moins "
        "une observation, formulation ou angle qu'on ne trouverait PAS dans un article générique "
        "typique sur ce même sujet (le genre de contenu qu'on trouve dans les 10 premiers résultats "
        "d'une recherche Google) ? Cherche une vraie prise de position, une observation contre-"
        "intuitive, un exemple concret inhabituel — pas juste une reformulation d'un savoir déjà "
        "largement diffusé.\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"has_surprise_moment": true|false, "excerpt": "extrait qui illustre le moment de surprise, '
        'ou vide si aucun", "reasoning": "justification en une phrase"}'
    )
    try:
        result = provider.generate_json(prompt, schema_hint="json surprise judgment object")
        if isinstance(result, dict) and "has_surprise_moment" in result:
            score = 100.0 if result["has_surprise_moment"] else 0.0
            return {"status": "success", "score": score, **result}
        return {"status": "error", "message": "Invalid response format", "score": None}
    except Exception as exc:
        logger.warning("Surprise moment judge agent failed: %s", exc)
        return {"status": "error", "message": str(exc), "score": None}
