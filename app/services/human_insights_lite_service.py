"""HumanInsightsLiteService — Variante légère de l'extraction d'insights humains.

Ne fait appel qu'aux extracteurs rapides et sans scraping lourd :
  - Google Autocomplete (JSON public, sans JS)
  - People Also Ask (fallback httpx ; playwright seulement s'il est dispo)
  - Forums détectés dans les résultats SERP (si serp_results fournis)
  - Snippets SERP (matière textuelle des résultats, sans fetch de page)

Exclut volontairement Reddit, Nitter, Quora, YouTube et le scraping de pages
concurrentes : exécution courte et prévisible, idéal en repli quand l'extracteur
complet échoue ou renvoie zéro insight. Même format de sortie que
human_insights_service.extract_human_insights.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def extract_human_insights_lite(
    keyword: str,
    serp_results: list[dict] | None = None,
    language: str = "fr",
) -> dict:
    """
    Version légère : Google Autocomplete + PAA (+ forums SERP si dispo).
    Retourne le même dict que l'extracteur complet — compatible avec le
    contexte de l'orchestrateur et le guard FIX 4.
    """
    from app.services.seo.human_insights_service import (
        _classify,
        _extract_forums_from_serp,
        _extract_google_autocomplete,
        _extract_people_also_ask,
    )

    all_insights = []
    extractors = [
        ("Google Autocomplete", lambda: _extract_google_autocomplete(keyword)),
        ("People Also Ask", lambda: _extract_people_also_ask(keyword)),
    ]
    if serp_results:
        extractors.append(("Forums SERP", lambda: _extract_forums_from_serp(keyword, serp_results)))

    sources_scraped: list[str] = []
    sources_failed: list[str] = []

    for name, extractor in extractors:
        try:
            results = extractor()
            all_insights.extend(results)
            if results:
                sources_scraped.append(f"{name} ({len(results)} insights)")
            else:
                sources_failed.append(f"{name} (0 résultats)")
        except Exception as exc:
            logger.warning("%s extractor error: %s", name, exc)
            sources_failed.append(f"{name} (erreur: {exc})")

    all_insights.sort(key=lambda x: x.engagement, reverse=True)

    seen: set[str] = set()
    aggregated: dict[str, list[str]] = {
        "questions": [],
        "pain_points": [],
        "real_examples": [],
        "objections": [],
        "positive_experiences": [],
        "debates": [],
        "vocabulary": [],
    }
    all_insights_dicts: list[dict] = []

    for insight in all_insights:
        content = insight.content.strip()
        if not content or len(content) < 15 or content in seen:
            continue
        seen.add(content)
        t = insight.insight_type
        key = {
            "question": "questions",
            "pain_point": "pain_points",
            "real_example": "real_examples",
            "objection": "objections",
            "positive": "positive_experiences",
            "debate": "debates",
        }.get(t, "vocabulary")
        aggregated[key].append(content)
        all_insights_dicts.append({
            "source_type": insight.source_type,
            "source_name": insight.source_name,
            "source_url": insight.source_url,
            "content": content,
            "insight_type": t,
            "author": insight.author,
            "engagement": insight.engagement,
        })

    status = "completed" if all_insights_dicts else "no_results"

    return {
        "keyword": keyword,
        "status": status,
        "total_insights": len(all_insights_dicts),
        "questions": aggregated["questions"],
        "pain_points": aggregated["pain_points"],
        "real_examples": aggregated["real_examples"],
        "objections": aggregated["objections"],
        "positive_experiences": aggregated["positive_experiences"],
        "debates": aggregated["debates"],
        "vocabulary": aggregated["vocabulary"],
        "all_insights": all_insights_dicts,
        "sources_scraped": sources_scraped,
        "sources_failed": sources_failed,
        "lite": True,
    }
