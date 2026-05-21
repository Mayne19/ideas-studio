from __future__ import annotations

from app.schemas.seo_workflow import ResearchBrief, asdict
from app.services.seo.adapters.serp_adapter import serp_adapter
from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter


def build_research_brief(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
) -> ResearchBrief:
    brief = ResearchBrief()

    if serp_adapter.configured:
        results = serp_adapter.search(keyword, limit=5)
        if results:
            brief.research_status = "available"
            for r in results:
                brief.sources_consulted.append(r)
                extracted = content_extraction_adapter.extract_headings(r["url"])
                for h in extracted:
                    if h["level"] == 2 or h["level"] == 3:
                        brief.competitor_angles.append(f"{h['text']} (from {r['title']})")
            brief.limitations.append("SERP research used limited results")
            return brief

    brief.research_status = "not_available"
    brief.limitations = [
        "SERP provider not configured (SERP_API_KEY missing)",
        "Research based on internal context only, no real competitor analysis",
    ]
    return brief


def build_research_brief_dict(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
) -> dict:
    return asdict(build_research_brief(keyword, title, category_name, serp_enabled))
