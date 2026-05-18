from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256


def list_google_watch_sources() -> list[dict]:
    return [
        {
            "key": "search_status_dashboard",
            "name": "Google Search Status Dashboard",
            "url": "https://status.search.google.com/",
            "kind": "status",
            "recommended_frequency": "daily",
            "official": True,
        },
        {
            "key": "search_status_faq",
            "name": "Google Search Status Dashboard FAQ",
            "url": "https://developers.google.com/search/help/status-dashboard",
            "kind": "documentation",
            "recommended_frequency": "daily",
            "official": True,
        },
        {
            "key": "search_central",
            "name": "Google Search Central",
            "url": "https://developers.google.com/search/",
            "kind": "documentation",
            "recommended_frequency": "daily",
            "official": True,
        },
        {
            "key": "seo_starter_guide",
            "name": "Google SEO Starter Guide",
            "url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
            "kind": "guide",
            "recommended_frequency": "weekly",
            "official": True,
        },
        {
            "key": "helping_creators",
            "name": "Helping creators - How Google Search Works",
            "url": "https://www.google.com/intl/en_us/search/howsearchworks/our-approach/helping-creators/",
            "kind": "guidance",
            "recommended_frequency": "weekly",
            "official": True,
        },
    ]


def normalize_update_item(item: dict) -> dict:
    source_key = (item.get("source_key") or "unknown").strip()
    title = (item.get("title") or "Untitled update").strip()
    summary = (item.get("summary") or "").strip()
    url = (item.get("url") or "").strip()
    published_at = item.get("published_at")
    if isinstance(published_at, datetime):
        published_iso = published_at.astimezone(timezone.utc).isoformat()
    elif published_at:
        published_iso = str(published_at)
    else:
        published_iso = None

    fingerprint_input = "||".join([source_key, title, summary, url, published_iso or ""])
    return {
        "source_key": source_key,
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_iso,
        "fingerprint": sha256(fingerprint_input.encode("utf-8")).hexdigest(),
    }


def classify_update_impact(item: dict) -> str:
    haystack = " ".join(
        str(item.get(key, "")).lower()
        for key in ("title", "summary", "kind", "category")
    )

    critical_terms = (
        "outage",
        "security",
        "manual action",
        "deindex",
        "de-index",
        "critical",
    )
    important_terms = (
        "core update",
        "ranking update",
        "spam update",
        "indexing issue",
        "serving issue",
        "crawl issue",
        "policy update",
    )
    medium_terms = (
        "documentation update",
        "new guidance",
        "clarification",
        "best practices",
        "starter guide",
        "helpful content",
    )

    if any(term in haystack for term in critical_terms):
        return "critical"
    if any(term in haystack for term in important_terms):
        return "important"
    if any(term in haystack for term in medium_terms):
        return "medium"
    return "low"


def build_action_recommendations(item: dict, impact: str | None = None) -> list[str]:
    impact = impact or classify_update_impact(item)
    haystack = " ".join(
        str(item.get(key, "")).lower()
        for key in ("title", "summary", "kind", "category")
    )
    recommendations: list[str] = []

    if "ranking" in haystack or "core update" in haystack:
        recommendations.append("Review recently declining articles and compare them against current intent and quality expectations.")
        recommendations.append("Prioritize refreshes for pages with weak first-answer structure, thin sections, or missing sources.")

    if "index" in haystack or "crawl" in haystack or "serving" in haystack:
        recommendations.append("Verify crawlability, canonical signals, and public rendering for key article pages.")
        recommendations.append("Check that sitemap and internal linking still surface priority content clearly.")

    if "documentation" in haystack or "guide" in haystack or "guidance" in haystack:
        recommendations.append("Compare the updated guidance against internal SEO rules and revise the knowledge pack if needed.")

    if "helpful content" in haystack or "creator" in haystack:
        recommendations.append("Audit whether generated drafts answer the reader quickly and avoid generic AI-sounding filler.")

    if impact == "critical":
        recommendations.append("Escalate this update for same-day review and annotate affected projects or articles.")
    elif impact == "important":
        recommendations.append("Add this update to the weekly SEO review queue with article refresh candidates.")
    elif impact == "medium":
        recommendations.append("Capture the change in the SEO watch log and review it during the next editorial audit.")
    else:
        recommendations.append("Store this item for reference; no immediate action is required unless related metrics move.")

    return recommendations
