from __future__ import annotations

from app.schemas.seo_workflow import ExternalLinkPlan, asdict


def build_external_link_plan(
    keyword: str,
    research_brief: dict | None = None,
) -> ExternalLinkPlan:
    plan = ExternalLinkPlan()

    research = research_brief or {}
    sources = research.get("sources_consulted", [])

    for src in sources:
        if isinstance(src, dict) and src.get("url"):
            plan.links.append({
                "url": src["url"],
                "anchor_text": src.get("title", "Source"),
                "placement": "auto",
                "reason": "Source consultée lors de la recherche",
                "source_reliability": "medium",
                "nofollow_recommended": True,
            })

    if not plan.links:
        plan.limitations = [
            "No external sources available",
            "SERP provider not configured for real research",
        ]

    return plan


def build_external_link_plan_dict(keyword: str, research_brief: dict | None = None) -> dict:
    return asdict(build_external_link_plan(keyword, research_brief))
