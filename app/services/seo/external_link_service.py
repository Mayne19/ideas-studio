from __future__ import annotations

import logging

from app.schemas.seo_workflow import ExternalLinkPlan, asdict
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)


def build_external_link_plan(
    keyword: str,
    research_brief: dict | None = None,
    project_id: str | None = None,
) -> ExternalLinkPlan:
    plan = ExternalLinkPlan()

    research = research_brief or {}
    sources = research.get("sources_consulted", [])

    # Also pick up URLs discovered by Scrapling during competitor scraping
    discovered_urls: list[str] = [
        url for url in research.get("facts_to_include", [])
        if url.startswith("http")
    ]

    candidate_links: list[dict] = []

    for src in sources:
        if not isinstance(src, dict):
            continue
        url = src.get("url", "")
        if not url:
            continue
        quality_check = src.get("quality_check", {})
        if quality_check.get("skipped") or not quality_check.get("reliable", True):
            # Skip if explicitly validated and found unreliable
            if quality_check.get("reachable") is False:
                continue
        candidate_links.append({
            "url": url,
            "anchor_text": src.get("title", "Source"),
            "placement": "auto",
            "reason": "Source consultée lors de la recherche",
            "source_reliability": quality_check.get("quality", "medium"),
            "nofollow_recommended": True,
            "word_count": quality_check.get("word_count", 0),
        })

    # Add discovered external links (deduplicated)
    existing_urls = {lk["url"] for lk in candidate_links}
    for url in discovered_urls:
        if url not in existing_urls:
            existing_urls.add(url)
            # Validate via Scrapling only if configured
            if scrapling_adapter.configured:
                check = scrapling_adapter.validate_url(url)
                if not check.get("reachable"):
                    continue
                quality = check.get("quality", "unknown")
                word_count = check.get("word_count", 0)
            else:
                quality = "unknown"
                word_count = 0
            candidate_links.append({
                "url": url,
                "anchor_text": url,
                "placement": "auto",
                "reason": "Lien découvert chez un concurrent",
                "source_reliability": quality,
                "nofollow_recommended": True,
                "word_count": word_count,
            })

    # Sort: prefer higher word_count (more content-rich sources)
    candidate_links.sort(key=lambda x: x.get("word_count", 0), reverse=True)
    plan.links = candidate_links[:8]

    if not plan.links:
        plan.limitations = [
            "No external sources available",
            "SERP provider not configured for real research",
        ]
    else:
        if scrapling_adapter.configured:
            plan.limitations.append("Sources validated via Scrapling")

    return plan


def build_external_link_plan_dict(
    keyword: str,
    research_brief: dict | None = None,
    project_id: str | None = None,
) -> dict:
    return asdict(build_external_link_plan(keyword, research_brief, project_id))
