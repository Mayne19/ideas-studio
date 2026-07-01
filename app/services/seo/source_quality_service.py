from __future__ import annotations

import logging

from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)

_MIN_WORD_COUNT = 150


def validate_sources(sources: list[dict]) -> list[dict]:
    """
    For each source dict (must have a 'url' key), verify reachability and
    content quality via Scrapling. Returns a new list with a 'quality_check'
    sub-dict added to each entry.
    """
    if not scrapling_adapter.configured:
        return [
            {**src, "quality_check": {"skipped": True, "reason": "scrapling_not_configured"}}
            for src in sources
        ]

    validated = []
    for src in sources:
        url = src.get("url", "")
        if not url:
            validated.append({**src, "quality_check": {"skipped": True, "reason": "no_url"}})
            continue
        check = scrapling_adapter.validate_url(url)
        quality = {
            "reachable": check.get("reachable", False),
            "word_count": check.get("word_count", 0),
            "quality": check.get("quality", "unknown"),
            "reliable": check.get("reachable", False) and check.get("word_count", 0) >= _MIN_WORD_COUNT,
        }
        if not quality["reachable"]:
            quality["error"] = check.get("error", "unreachable")
        validated.append({**src, "quality_check": quality})
        logger.debug("source_quality %s → %s", url, quality["quality"])

    return validated


def filter_reliable_sources(sources: list[dict]) -> list[dict]:
    """Return only sources that passed quality validation."""
    return [s for s in sources if s.get("quality_check", {}).get("reliable", False)]
