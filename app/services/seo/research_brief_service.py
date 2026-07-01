from __future__ import annotations

import logging

from app.schemas.seo_workflow import ResearchBrief, asdict
from app.services.seo.adapters.serp_adapter import serp_adapter
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)


def build_research_brief(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
    project_id: str | None = None,
) -> ResearchBrief:
    brief = ResearchBrief()

    if not serp_adapter.configured:
        brief.research_status = "not_available"
        brief.limitations = [
            "SERP provider not configured (SERP_API_KEY missing)",
            "Research based on internal context only, no real competitor analysis",
        ]
        return brief

    results = serp_adapter.search(keyword, limit=5)
    if not results:
        brief.research_status = "not_available"
        brief.limitations = ["SERP returned no results"]
        return brief

    brief.research_status = "available"
    external_links_discovered: list[dict] = []

    for r in results:
        url = r.get("url", "")
        if not url:
            continue

        # Scrapling full competitor scrape
        if scrapling_adapter.configured:
            competitor = scrapling_adapter.scrape_competitor(url)
            if "error" not in competitor:
                source_entry = {
                    "url": url,
                    "title": competitor.get("title") or r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "word_count": competitor.get("word_count", 0),
                    "meta_description": competitor.get("meta_description", ""),
                }
                brief.sources_consulted.append(source_entry)

                for h in competitor.get("headings", []):
                    if h["level"] in (2, 3):
                        brief.competitor_angles.append(
                            f"{h['text']} (from {competitor.get('title') or r.get('title', url)})"
                        )

                for lk in competitor.get("external_links_discovered", []):
                    if lk not in external_links_discovered:
                        external_links_discovered.append(lk)
            else:
                # Fallback: use SERP snippet only
                brief.sources_consulted.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})
        else:
            brief.sources_consulted.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})

    # Attach discovered external links as a field_signal for the orchestrator
    if external_links_discovered:
        brief.field_signals.append(
            f"{len(external_links_discovered)} liens externes découverts chez les concurrents"
        )
    # Store raw list for ExternalLinkPlan
    brief.facts_to_include.extend(
        [lk.get("url", "") for lk in external_links_discovered[:10] if lk.get("url")]
    )

    brief.limitations.append("SERP research used limited results (5 URLs max)")
    return brief


def build_research_brief_dict(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
    project_id: str | None = None,
) -> dict:
    return asdict(build_research_brief(keyword, title, category_name, serp_enabled, project_id))
